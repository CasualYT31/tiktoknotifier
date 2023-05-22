"""MIT License

Copyright (c) 2023 CasualYouTuber31

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""Code that runs the bot."""

# discord.py Imports.
import discord
from discord.ext import commands

# TikTokNotifier Imports.
from read_token import read_token

def initialise_bot(command_prefix: str="?"):
    """Sets up and runs the bot.
    
    Parameters
    ----------
    command_prefix : str
        The prefix to denote commands.
    
    Raises
    ------
    SystemExit
        If the token for the bot could not be read.
    """

    # Read the token from "./token.txt".
    TOKEN = read_token()
    # Initialise the bot.
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=command_prefix, intents=intents)
    # Setup the bot's code.
    @client.event
    async def on_ready():
        print('Connected to bot: {}'.format(client.user.name))
        print('Bot ID: {}'.format(client.user.id))
    # Launch the bot.
    client.run(TOKEN)
