# tiktoknotifier
This is a Discord bot that polls configured TikTok user pages to see if they have submitted new uploads or gone live, and notify relevant users via Direct Message.

## Dependencies
This bot requires Python 3.11 or later due to use of `StrEnum`.
You will need to install `discord.py` to run this code.

## Token
In order to run this bot via a Discord application, you will have to create a new text file called `token.txt`, save it in the same folder as `main.py` (or from wherever you are running the bot), and paste your bot's token on the first line.

## Intents
You will also need to grant your application the `Message Content Intent`.
