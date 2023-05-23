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
from config import update_setting, Setting, delete_discord_user, \
    get_all_users_for_discord_user, get_user_for_discord_user, get_text_for_settings
from polling import PollingCog

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

    # Once the bot is ready, begin polling TikTok.
    @client.event
    async def on_ready():
        await client.add_cog(PollingCog(client))

    # Setup the `notify` command.
    @client.command()
    async def notify(ctx, username, option="all"):
        user_id = str(ctx.author.id)
        username = username.lower()
        option = option.lower()
        if option != "all" and option != "videos" and option != "lives" and \
            option != "none":
            await ctx.send("Please provide the following for the second "
                           "parameter:\n- `all` to be notified of both lives and "
                           "new videos (default).\n- `videos` to be notified of "
                           "videos only.\n- `lives` to be notified of lives only.\n"
                           "- `none` to stop all notifications for the user "
                           f"`@{username}`.")
            return
        elif option == "all":
            update_setting(username, user_id, Setting.VIDEOS, True)
            update_setting(username, user_id, Setting.LIVES, True)
            await ctx.send(f'Okay, I will DM you when `@{username}` uploads new '
                           'videos and when they go live!')
        elif option == "videos":
            update_setting(username, user_id, Setting.VIDEOS, True)
            update_setting(username, user_id, Setting.LIVES, False)
            await ctx.send(f'Okay, I will DM you when `@{username}` uploads new '
                           'videos, but not when they go live!')
        elif option == "lives":
            update_setting(username, user_id, Setting.VIDEOS, False)
            update_setting(username, user_id, Setting.LIVES, True)
            await ctx.send(f'Okay, I will DM you when `@{username}` goes live, but '
                           'not when they upload new videos!')
        elif option == "none":
            delete_discord_user(username, user_id)
            await ctx.send(f'Okay, I will **not** DM you when `@{username}` '
                           'uploads new videos or when they go live!')
    @notify.error
    async def notify_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide the username of the TikTok account you "
                           "want to be notified of!")
    
    # Setup the `list` command.
    @client.command()
    async def list(ctx, username=""):
        # For a simple bot, with not many users, this suffices. On larger scales
        # this is not such a good idea, though.
        user_id = str(ctx.author.id)
        username = username.lower()
        if username != "":
            settings = get_user_for_discord_user(username, user_id)
            if settings:
                what_for = get_text_for_settings(
                    videos=settings[Setting.VIDEOS], lives=settings[Setting.LIVES])
                await ctx.send("You are currently set to receive notifications for "
                               f"`@{username}`'s {what_for}.")
            else:
                await ctx.send("You are currently set to receive **no** "
                               f"notifications for `@{username}`.")
        else:
            usernames = get_all_users_for_discord_user(user_id)
            if usernames:
                # Would need to handle character limit for many usernames, if
                # operating on a large scale.
                msg = ""
                for username, settings in usernames.items():
                    what_for = get_text_for_settings(
                        videos=settings[Setting.VIDEOS],
                        lives=settings[Setting.LIVES])
                    msg += f"`@{username}`: {what_for}.\n"
                await ctx.send(msg)
            else:
                await ctx.send("You are currently set to receive no notifications.")
    
    # Launch the bot.
    client.run(TOKEN)
