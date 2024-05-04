# squawk-bot
A bot to organize all the pelican-eggs repos

## Python
This aplication needs python 3.10.x or lower.

## Variables

|Variable|Description|
|:--------:|:-----------:|
|DISCORD_CHANNEL_ID|The channel id of the forum channel where the threads should be made in|
|DISCORD_BOT_TOKEN|THe discord bot token, get at: https://discord.dev|
|GITHUB_ACCESS_TOKEN|A github acces token if you want to support private repo's (Can not be a classic one)|
|GITHUB_REPO_NAMES|The repo's the bot should be looking at its issues and pull requests|
|GITHUB_FETCH_INTERVAL_TIME|The timeout in seconds a repo should be checked|

## Stoping
To stop this bot, first send ^C (CTRL+C) and then `quit` or `exit`.