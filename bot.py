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
from config import update_setting, Setting, delete_discord_user, delete_setting, \
    get_all_users_for_discord_user, get_user_for_discord_user, \
    get_text_for_settings, find_group_of_username
from poller import PollingCog, GROUP_COUNT
from stats import summarise_stats, reset_stats

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

    # Read bot maintainer's user ID from "./owner.txt".
    with open("./owner.txt", mode='r', encoding='utf-8') as owner_txt:
        OWNER_ID = owner_txt.read().strip()

    # Initialise the bot.
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=command_prefix, intents=intents,
                          help_command=None)
    
    # Custom help command.
    @client.command()
    async def help(ctx):
        await ctx.send("TikTok bot that polls a user account every ~3 seconds.\n"
                       "Use `?notify username [all/videos/lives/none/monitor]` to "
                       "configure "
                       "which users you receive notifications for (defaults to "
                       "`all`). Use `?list [username]` to list your notification "
                       "configurations.\n"
                       "Use `?filter username [filters...]` to apply filters to "
                       "video captions. This means you'll only get a video "
                       "notification for the given user if their video's caption "
                       "has at least one of the words or phrases you give to the "
                       "command. E.g. `?filter abc123 hi #meme \"Filter "
                       "Challenge\"` will mean that new uploads will only be "
                       "reported if their caption contains one of \"hi\", "
                       "\"meme\", or \"Filter Challenge\". You can issue no "
                       "filters to remove the filters applied to the user. If a "
                       "user has no filters (default), all video uploads will be "
                       "reported.\n"
                       "Use `?stats get [username]` to get stats on how polling is "
                       "doing (success rate, reasons for failures for each user, "
                       "etc.). If no username is given, all stats across each user "
                       "will be tallied and summarised.")

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
            option != "none" and option != "monitor":
            await ctx.send("Please provide the following for the second "
                           "parameter:\n- `all` to be notified of both lives and "
                           "new videos (default).\n- `videos` to be notified of "
                           "videos only.\n- `lives` to be notified of lives only.\n"
                           "- `none` to stop all notifications for the user "
                           f"`@{username}`.\n- `monitor` to be notified of when a "
                           "user account can be found or cannot be found. You "
                           "cannot receive notifications for videos or lives for "
                           "this account.")
            return
        elif option == "all":
            update_setting(username, user_id, Setting.VIDEOS, True)
            update_setting(username, user_id, Setting.LIVES, True)
            delete_setting(username, user_id, Setting.MONITOR)
            await ctx.send(f'Okay, I will DM you when `@{username}` uploads new '
                           'videos and when they go live!')
        elif option == "videos":
            update_setting(username, user_id, Setting.VIDEOS, True)
            update_setting(username, user_id, Setting.LIVES, False)
            delete_setting(username, user_id, Setting.MONITOR)
            await ctx.send(f'Okay, I will DM you when `@{username}` uploads new '
                           'videos, but not when they go live!')
        elif option == "lives":
            update_setting(username, user_id, Setting.VIDEOS, False)
            update_setting(username, user_id, Setting.LIVES, True)
            delete_setting(username, user_id, Setting.MONITOR)
            await ctx.send(f'Okay, I will DM you when `@{username}` goes live, but '
                           'not when they upload new videos!')
        elif option == "monitor":
            update_setting(username, user_id, Setting.VIDEOS, False)
            update_setting(username, user_id, Setting.LIVES, False)
            update_setting(username, user_id, Setting.MONITOR, True)
            await ctx.send(f'Okay, I will DM you when the `@{username}` account '
                           'becomes available or unavailable.')
        elif option == "none":
            delete_discord_user(username, user_id)
            await ctx.send(f'Okay, I will **not** DM you when `@{username}` '
                           'uploads new videos or when they go live!')
    @notify.error
    async def notify_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide the username of the TikTok account you "
                           "want to be notified of!")
    
    # Setup the `filter` command.
    @client.command()
    async def filter(ctx, username: str, *filters: str):
        user_id = str(ctx.author.id)
        username = username.lower()
        # Grab a copy of the current filters, if they exist.
        settings = get_user_for_discord_user(username, user_id)
        if Setting.FILTER in settings:
            old_filters = settings[Setting.FILTER].copy()
        else:
            old_filters = []
        # Replace the old filters with new ones. If no filters are given, remove
        # them!
        new_filters = []
        for f in filters:
            new_filters.append(f)
        if len(new_filters) == 0:
            delete_setting(username, user_id, Setting.FILTER)
            await ctx.send(f"Removed the following filters from `@{username}`:\n"
                           f"```\n{old_filters}\n```")
        else:
            # If VIDEOS and LIVES settings aren't set yet, initialise them.
            if Setting.VIDEOS not in settings:
                update_setting(username, user_id, Setting.VIDEOS, True)
                await ctx.send(f"You are now being notified when `@{username}` "
                               "uploads a video.")
            if Setting.LIVES not in settings:
                update_setting(username, user_id, Setting.LIVES, False)
            # Update FILTER setting.
            update_setting(username, user_id, Setting.FILTER, new_filters)
            await ctx.send(f"Added new filters to `@{username}`:\n"
                           f"```\n{new_filters}\n```\n"
                           f"Old filters:\n```\n{old_filters}\n```")
    @filter.error
    async def filter_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide the username of the TikTok account you "
                           "want to apply filters to!")
    
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
                group_number, index, username_count = \
                    find_group_of_username(username, GROUP_COUNT)
                group_msg = "no group" if group_number is None else \
                    f"group {group_number + 1} of {GROUP_COUNT}, " \
                    f"user {index + 1} of {username_count}"
                what_for = get_text_for_settings(
                    videos=settings[Setting.VIDEOS], lives=settings[Setting.LIVES],
                    monitor=Setting.MONITOR in settings)
                filters = ""
                if Setting.FILTER in settings:
                    filters = " Filters applied to video uploads: `" \
                              f"{settings[Setting.FILTER]}`."
                alarm_setting = ""
                if user_id == OWNER_ID:
                    if Setting.ALARM in settings and settings[Setting.ALARM]:
                        alarm_setting = " **You will receive an alarm when this " \
                            "account goes LIVE!**"
                await ctx.send("You are currently set to receive notifications for "
                            f"`@{username}`'s __{what_for}__. They are in "
                            f"{group_msg}.{filters}{alarm_setting}")
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
                    group_number, index, username_count = \
                        find_group_of_username(username, GROUP_COUNT)
                    group_msg = "---" if group_number is None else \
                        f"Group {group_number + 1} of {GROUP_COUNT}, " \
                        f"User {index + 1} of {username_count}"
                    what_for = get_text_for_settings(
                        videos=settings[Setting.VIDEOS],
                        lives=settings[Setting.LIVES],
                        monitor=Setting.MONITOR in settings)
                    filters = ""
                    if Setting.FILTER in settings:
                        filters = " Filters applied to videos: " \
                                 f"`{settings[Setting.FILTER]}`."
                    alarm_setting = ""
                    if user_id == OWNER_ID:
                        if Setting.ALARM in settings and settings[Setting.ALARM]:
                            alarm_setting = " **You will receive an alarm when " \
                                "this account goes LIVE!**"
                    msg += f"`@{username}` ({group_msg}): __{what_for}__." \
                        f"{filters}{alarm_setting}\n"
                await ctx.send(msg)
            else:
                await ctx.send("You are currently set to receive no notifications.")
    
    # Setup the `stats` command.
    @client.command()
    async def stats(ctx, sub_command: str, username: str=""):
        user_id = str(ctx.author.id)
        cmd = sub_command.lower()
        username = username.lower()
        if cmd == "get":
            msg = summarise_stats(username)
            await ctx.send(msg)
        elif cmd == "reset":
            if (user_id == OWNER_ID):
                reset_stats()
                await ctx.send("Removed all stats!")
            else:
                await ctx.send("Only the bot's owner is allowed to use this "
                               "command!")
        else:
            await ctx.send(f"`{sub_command}` is an invalid sub-command!")
    @stats.error
    async def stats_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide either the `get` or `reset` "
                           "sub-command, e.g. `?stats get`.")
    
    # Setup the `alarm` admin command.
    @client.command()
    async def alarm(ctx, username, flag: bool):
        # Only allow the maintainer of the bot to operate this command!
        user_id = str(ctx.author.id)
        username = username.lower()
        if (user_id != OWNER_ID):
            await ctx.send("Only the bot's owner is allowed to use this command!")
            return
        # Set alarm property for the given user.
        if flag:
            # If VIDEOS and LIVES settings aren't set yet, initialise them.
            settings = get_user_for_discord_user(username, user_id)
            if Setting.VIDEOS not in settings:
                update_setting(username, user_id, Setting.VIDEOS, False)
            if Setting.LIVES not in settings:
                update_setting(username, user_id, Setting.LIVES, True)
                await ctx.send(f"You are now being notified when `@{username}` "
                               "goes LIVE.")
            update_setting(username, user_id, Setting.ALARM, True)
        else:
            delete_setting(username, user_id, Setting.ALARM)
        await ctx.send(f"Setting `@{username}`'s alarm setting to {flag}.")
    @alarm.error
    async def alarm_error(ctx, error):
        if isinstance(error, commands.BadBoolArgument):
            await ctx.send("The second argument must be a bool parameter!")
    
    # Launch the bot.
    client.run(TOKEN)
