import discord
from github import Github, Auth
import threading
import asyncio
import json
from datetime import datetime
import os
from dotenv import load_dotenv, dotenv_values 

load_dotenv()

GITHUB_REPO_NAMES = os.getenv("GITHUB_REPO_NAMES", "").split(",")
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
GITHUB_ACCESS_TOKEN = os.getenv('GITHUB_ACCESS_TOKEN')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GITHUB_FETCH_INTERVAL_TIME= int(os.getenv('GITHUB_FETCH_INTERVAL_TIME'))

# Authentication
if GITHUB_ACCESS_TOKEN:
    auth = Auth.Token(GITHUB_ACCESS_TOKEN)
    github = Github(auth=auth)
else:
    github = Github()

client = discord.Client(intents=discord.Intents.all())

# Function to save thread_dict to file
def save_thread_dict():
    with open("thread_data.json", "w") as f:
        json.dump(thread_dict, f, indent=4) # Prity the log file, multiline

# Function to load thread_dict from file
def load_thread_dict():
    try:
        with open("thread_data.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# In on_ready event:
thread_dict = load_thread_dict()

# Function to create a new log file
def create_log_file():
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    log_folder = os.path.join("logs", timestamp)
    os.makedirs(log_folder, exist_ok=True)
    log_file = os.path.join(log_folder, f"log_{timestamp}.txt")
    return log_file

# Create initial log file
log_file = create_log_file()

# Function to write a message to the log file
def log(message):
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

# Function to create a thread in the Discord channel
async def create_thread(issue_or_pr, channel_id, repo_name):
    channel = client.get_channel(channel_id)
    if not channel:
        print(f"Error: Discord channel '{channel_id}' not found.")
        log(f"Error: Discord channel '{channel_id}' not found.")
        return

    
    title = issue_or_pr.title
    is_pull_request = hasattr(issue_or_pr, 'pull_request') and issue_or_pr.pull_request is not None
    type_str = "Pull Request" if is_pull_request else "Issue"
    content = f"**New {type_str} in {repo_name}:** {issue_or_pr.html_url}" # The first message that is send
    try:
        thread = await channel.create_thread(name=title, auto_archive_duration=1440, content=content)
        thread_dict[f"{repo_name}:{issue_or_pr.number}"] = {"thread_id": thread.thread.id, "is_pull_request": is_pull_request}
        log(f"Created thread '{title}' for {issue_or_pr.html_url}")
        save_thread_dict()  # Save thread_dict to file after creating thread
    except Exception as e:
        print(f"Error: {e}")
        log(f"Error creating thread: {e}")

# Function to monitor issues and PRs for changes
async def monitor_github(exit_event):
    while not exit_event.is_set():
        try:
            for repo_name in GITHUB_REPO_NAMES:
                repo = github.get_repo(repo_name)
                for issue in repo.get_issues(state="open"):
                    if f"{repo_name}:{issue.number}" not in thread_dict:
                        await create_thread(issue, DISCORD_CHANNEL_ID, repo_name)

                for pull_request in repo.get_pulls(state="open"):
                    if f"{repo_name}:{pull_request.number}" not in thread_dict:
                        await create_thread(pull_request, DISCORD_CHANNEL_ID, repo_name)

            # Check for updates in existing threads (improved)
            for key, thread_info in list(thread_dict.items()):  # Convert to list to avoid concurrent modification issues
                repo_name, issue_or_pr_number = key.split(":")
                repo = github.get_repo(repo_name)
                issue_or_pr = repo.get_pull(int(issue_or_pr_number)) if thread_info["is_pull_request"] else repo.get_issue(int(issue_or_pr_number))
                thread = client.get_channel(DISCORD_CHANNEL_ID).get_thread(thread_info["thread_id"])
                if issue_or_pr.title != thread.name:
                    old_title = thread.name
                    await thread.edit(name=issue_or_pr.title)
                    print(f"Thread title edited: '{old_title}' -> '{issue_or_pr.title}'")
                    log(f"Thread title edited: '{old_title}' -> '{issue_or_pr.title}'")                    
                if issue_or_pr.state == "closed":
                    await thread.send(f"The {'Pull Request' if thread_info['is_pull_request'] else 'Issue'} has been closed or merged. This thread will now be locked.")  # Message before locking                    
                    await thread.edit(locked=True)  # Lock the thread
                    print(f"Thread '{thread.name}' locked due to {'Pull Request' if thread_info['is_pull_request'] else 'Issue'} closure")
                    log(f"Thread '{thread.name}' locked due to {'Pull Request' if thread_info['is_pull_request'] else 'Issue'} closure")                    
                    del thread_dict[key]  # Remove closed thread from dictionary

            save_thread_dict()  # Save thread_dict to file after monitoring

        except Exception as e:
            print(f"Error: {e}")
            log(f"Error: {e}")

        await asyncio.sleep(GITHUB_FETCH_INTERVAL_TIME) 

# Function to gracefully shutdown the bot
def shutdown_bot(exit_event):
    while True:
        command = input("Type 'exit' to shutdown: \n")
        if command.lower() == "exit":
            exit_event.set()
            break
        elif command.lower() == "quit":
            exit_event.set()
            break

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    log(f'Logged in as {client.user} (ID: {client.user.id})')    
    exit_event = threading.Event()
    monitor_task = asyncio.create_task(monitor_github(exit_event))  # Run monitor_github as a task
    shutdown_thread = threading.Thread(target=shutdown_bot, args=(exit_event,))
    shutdown_thread.start()

    await client.wait_until_ready()
    await monitor_task

client.run(DISCORD_BOT_TOKEN)
