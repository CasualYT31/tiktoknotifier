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

"""Polling cog to be added to the Discord bot."""

import traceback
import json
from subprocess import run
from threading import Lock
from http.cookies import SimpleCookie
from requests.cookies import RequestsCookieJar

from discord import File
from discord.ext import tasks, commands
from requests_html import AsyncHTMLSession
from numpy import array_split

from config import get_usernames_and_config, Setting
from stats import ReasonForFailure, record_successful_poll, record_failed_poll, \
    remove_user

class PollingCog(commands.Cog):
    def __init__(self, client):
        self.client = client

        # Load log channel ID.
        self.LOG_CHANNEL = ""
        try:
            with open("./log_channel.txt", mode='r', encoding='utf-8') as f:
                self.LOG_CHANNEL = f.read().strip()
        except Exception as e:
            print(f"Could not load log channel ID: {e}")

        # Load state.
        self.STATE_FILE_PATH = "./state.json"
        self.state_lock = Lock()
        try:
            with open(self.STATE_FILE_PATH, mode='r', encoding='utf-8') as f:
                self.state = json.loads(f.read())
        except Exception as e:
            self.state = {}
            print(f"COULDN'T LOAD STATE: {e}")

        # Load cookies: https://stackoverflow.com/a/49865026.
        self.raw_cookies = ""
        self.cookies = None
        self.load_cookies()

        # Load headers.
        self.headers = None
        try:
            with open("headers.json", mode='r', encoding='utf-8') as f:
                self.headers = json.loads(f.read())
        except Exception as e:
            print(f"Could not read headers! {e}")

        # Start polling.
        self.GROUP_COUNT = 2
        self.GROUP_COLOURS = [
            "\x1B[1;33m", # Yellow.
            "\x1B[1;36m", # Cyan.
        ]
        assert len(self.GROUP_COLOURS) == self.GROUP_COUNT
        self.poller_username_counters = [0] * self.GROUP_COUNT
        self.session = [AsyncHTMLSession()] * self.GROUP_COUNT
        self.poller_group1.start()
        self.poller_group2.start()
        self.clean_up_user_state.start()
        self.refresh_cookies.start()
    
    def cog_unload(self):
        self.poller_group1.cancel()
        self.poller_group2.cancel()
        self.clean_up_user_state.cancel()
        self.refresh_cookies.cancel()

    def load_cookies(self):
        try:
            raw_cookies = ""
            with open("cookie.txt", mode='r', encoding='utf-8') as cookie_file:
                raw_cookies = cookie_file.read()
            if raw_cookies != self.raw_cookies:
                self.raw_cookies = raw_cookies
                self.cookies = RequestsCookieJar()
                self.cookies.update(SimpleCookie(raw_cookies))
                return True
        except Exception as e:
            print(f"Could not read cookies! {e}")
        return False
    
    @tasks.loop(seconds=5.0)
    async def refresh_cookies(self):
        if self.load_cookies():
            await self.error("Refreshed cookies.")
    
    @tasks.loop(seconds=60.0)
    async def clean_up_user_state(self):
        """If the configurations for a user have been removed, then its
        state and stats should also be removed."""
        
        # I am not going to bother with the extremely unlikely case of a user's
        # configuration being removed as it is being polled AND this task is
        # running.
        usernames, _ = get_usernames_and_config()
        for username in list(self.state.keys()):
            if username not in usernames:
                del self.state[username]
                remove_user(username)
        await self.write_state()
    
    @tasks.loop(seconds=3.0)
    async def poller_group1(self):
        try:
            await self.poll(0)
        except Exception as e:
            print(f"EXCEPTION IN GROUP 1: {e}")
            traceback.print_exc()
    
    @tasks.loop(seconds=3.0)
    async def poller_group2(self):
        try:
            await self.poll(1)
        except Exception as e:
            print(f"EXCEPTION IN GROUP 2: {e}")
            traceback.print_exc()

    async def poll(self, group_number: int):
        assert self.GROUP_COUNT > 0
        assert group_number >= 0 and group_number < self.GROUP_COUNT

        # Get the configuration and split up the groups to find the correct one.
        # If there aren't any usernames to poll, wait until there are.
        usernames, config = get_usernames_and_config()
        username_groups = array_split(usernames, self.GROUP_COUNT)
        usernames = username_groups[group_number].tolist()
        if len(usernames) == 0:
            return
        
        # Increment username counter, and adjust it if it falls out of range.
        # Then, submit GET request.
        username, response, counter_was_reset = \
            await self.get_next_user(usernames, group_number)
        if counter_was_reset:
            self.print_char(str(group_number), group_number)

        # Is TikTok beginning to deny access? In which case, ignore this request.
        if "Access Denied" in response.html.html:
            await self.error(f"Access denied when polling for @{username}!",
                             ReasonForFailure.ACCESS_DENIED, username, group_number,
                             response.html)
            record_failed_poll(username, ReasonForFailure.ACCESS_DENIED)
            return
        
        # In a similar vein, TikTok can have brief periods where it responds with an
        # incomplete web page that contains "Please wait..." Seems like something is
        # going wrong with the JavaScript. Rendering the page doesn't work, so we
        # will have to skip polls until it stops...
        if "Please wait..." in response.html.html:
            record_failed_poll(username, ReasonForFailure.PLEASE_WAIT)
            self.print_char('!', group_number)
            return
        
        # Are we monitoring this account, instead of reporting uploads and LIVES?
        monitor_account = any([Setting.MONITOR in settings for settings in
                               config[username].values()])
        is_available = True
        
        # If there is an element which has the 'DivErrorContainer', then something
        # is wrong with the page. Could be that it is a private account, or the
        # account doesn't exist, or they haven't uploaded anything yet. Report it in
        # the console and move on to the next user.
        div_elements = response.html.find('div')
        error_strings = self.check_for_error_div(div_elements)
        if len(error_strings) > 0:
            if monitor_account and \
                "couldn't find this account" in error_strings[0].strip().lower():
                is_available = False
            else:
                reason = self.record_error_div(username, error_strings[0])
                await self.error(f"Couldn't retrieve latest uploads for "
                                 f"@{username}: {error_strings}", reason, username,
                                 group_number, response.html)
                return
        
        # Find the latest video's ID and caption. If they couldn't be found, ignore
        # this user.
        if monitor_account:
            latest_video_id, latest_video_caption, error_string = -1, "", ""
        else:
            latest_video_id, latest_video_caption, error_string, reason = \
                self.find_latest_video(username, div_elements)
            if len(error_string) > 0:
                await self.error(error_string, reason, username, group_number,
                                 response.html)
                return
        
        # Is this user now LIVE?
        is_live = "SpanLiveBadge" in response.html.html
        
        # Update this user's state. Initialise state object for this user if it
        # doesn't already exist. And update the LIVE flags.
        previous_video_id = await self.update_user_state(username,
                                                         latest_video_id,
                                                         is_live,
                                                         is_available)
        
        if monitor_account:
            if not self.state[username]["wasAvailable"] and \
                self.state[username]["isAvailable"]:
                await self.notify_monitor(config, username, True)
            elif self.state[username]["wasAvailable"] and \
                not self.state[username]["isAvailable"]:
                await self.notify_monitor(config, username, False)
        else:
            # If the stored video ID is larger than the latest video ID, it's likely
            # the video became unavailable later. Send notification for it.
            # Otherwise,
            # if the latest video ID is larger, a new upload has been made, so send
            # notification for that, too. Only send notifications if this isn't the
            # first time a user's video ID has been retrieved.
            if previous_video_id >= 0:
                if previous_video_id > latest_video_id:
                    await self.notify_deleted_video(config, username, previous_video_id)
                elif previous_video_id < latest_video_id:
                    await self.notify_video(config, username, latest_video_id, \
                                            latest_video_caption)
        
            # If the user went LIVE, send notification.
            if not self.state[username]["wasLive"] and self.state[username]["isLive"]:
                await self.notify_live(config, username)
        
        # Indicate via console that this poll was successful.
        self.state[username]["previousError"] = ""
        self.state[username]["loggedError"] = False
        record_successful_poll(username)
        self.print_char('.', group_number)
    
    def print_char(self, char: str, group_number: int):
        print(f"{self.GROUP_COLOURS[group_number]}{char}", end='\x1B[0m',
              flush=True)

    async def get_next_user(self, usernames: list[str], group_number: int):
        """Returns tuple (username, response, was this group's user
        counter reset?)"""

        reset_counter = False
        self.poller_username_counters[group_number] += 1
        if self.poller_username_counters[group_number] >= len(usernames):
            self.poller_username_counters[group_number] = 0
            reset_counter = True
        username = usernames[self.poller_username_counters[group_number]]
        response = await self.session[group_number].get(
            f"https://www.tiktok.com/@{username}", cookies=self.cookies,
            headers=self.headers)
        return username, response, reset_counter
    
    def check_for_error_div(self, div_elements):
        """Returns empty list if there was no error div. Returns a list
        of error strings if there was an error div."""

        error_elements = [element for element in div_elements \
                    if "class" in element.attrs \
                    and any([True for css_class in element.attrs['class'] \
                             if 'DivErrorContainer' in css_class])]
        if len(error_elements) > 0:
            p_elements = error_elements[0].find('p')
            return [p.text for p in p_elements]
        return []

    def record_error_div(self, username: str, primary_error_string: str):
        estr = primary_error_string.strip().lower()
        if "something went wrong" in estr:
            record_failed_poll(username, ReasonForFailure.SOMETHING_WENT_WRONG)
            return ReasonForFailure.SOMETHING_WENT_WRONG
        elif "no content" in estr:
            record_failed_poll(username, ReasonForFailure.NO_CONTENT)
            return ReasonForFailure.NO_CONTENT
        elif "page not available" in estr:
            record_failed_poll(username, ReasonForFailure.PAGE_NOT_AVAILABLE)
            return ReasonForFailure.PAGE_NOT_AVAILABLE
        elif "private" in estr:
            record_failed_poll(username, ReasonForFailure.PRIVATE_ACCOUNT)
            return ReasonForFailure.PRIVATE_ACCOUNT
        else:
            record_failed_poll(username, ReasonForFailure.UNKNOWN_ERROR_DIV,
                               primary_error_string)
            return ReasonForFailure.UNKNOWN_ERROR_DIV
    
    def find_latest_video(self, username: str, div_elements):
        # First, find the div containing all the user's videos.
        video_list = [element for element in div_elements \
                      if "data-e2e" in element.attrs and \
                        element.attrs["data-e2e"] == "user-post-item-list"]
        if len(video_list) == 0:
            record_failed_poll(username, ReasonForFailure.USER_POST_ITEM_LIST)
            return -1, "", f"Could not retrieve video list for @{username}!", \
                ReasonForFailure.USER_POST_ITEM_LIST
        
        # Then, retrieve the list of videos within that div.
        video_list = video_list[0].find('div')
        if len(video_list) < 2:
            record_failed_poll(username, ReasonForFailure.USER_POST_ITEM_LIST_DIV)
            return -1, "", f"Could not retrieve videos within video list for " \
                           f"@{username}!", ReasonForFailure.USER_POST_ITEM_LIST_DIV
        
        # Find the first video in that list.
        first_video = video_list[1]
        video_div = [element for element in first_video.find('div') \
                     if 'data-e2e' in element.attrs and \
                        element.attrs['data-e2e'] == "user-post-item"]
        if len(video_div) != 1:
            record_failed_poll(username, ReasonForFailure.USER_POST_ITEM)
            return -1, "", f"Could not find video div for @{username}! " \
                           f"{video_div}", ReasonForFailure.USER_POST_ITEM
        
        # Find the link to the video in the first video's div.
        video_link = video_div[0].find('a', first=True)
        if video_link == None or 'href' not in video_link.attrs:
            record_failed_poll(username, ReasonForFailure.NO_VIDEO_LINK)
            return -1, "", f"Could not extract video link for @{username}! " \
                           f"{video_link}", ReasonForFailure.NO_VIDEO_LINK
        
        # Find the first video's description div.
        video_desc_div = [element for element in first_video.find('div') \
                     if 'data-e2e' in element.attrs and \
                        element.attrs['data-e2e'] == "user-post-item-desc"]
        if len(video_desc_div) != 1:
            record_failed_poll(username, ReasonForFailure.USER_POST_ITEM_DESC)
            return -1, "", f"Could not find video desc div for @{username}! " \
                           f"{video_desc_div}", ReasonForFailure.USER_POST_ITEM_DESC
        
        # Find the first video's description.
        # The title attribute should still be present even if the caption is blank.
        video_desc_link = video_desc_div[0].find('a', first=True)
        if video_desc_link == None or 'title' not in video_desc_link.attrs:
            record_failed_poll(username, ReasonForFailure.NO_VIDEO_DESC)
            return -1, "", f"Could not extract video desc for @{username}! " \
                           f"{video_desc_link}", ReasonForFailure.NO_VIDEO_DESC
        
        # Extract and return the information.
        latest_video_id = \
            video_link.attrs['href'][video_link.attrs['href'].rfind('/')+1:]
        latest_video_caption = video_desc_link.attrs['title']
        try:
            return int(latest_video_id), latest_video_caption, "", None
        except Exception as e:
            record_failed_poll(username, ReasonForFailure.FAULTY_VIDEO_LINK)
            return -1, "", f"Could not convert video ID to int for @{username}! " \
                           f"{latest_video_id}. {e}", \
                            ReasonForFailure.FAULTY_VIDEO_LINK
    
    async def update_user_state(self, username: str, latest_video_id: int,
                                is_live: bool, is_available: bool):
        if username not in self.state:
            self.state[username] = {
                "wasLive": False,
                "isLive": False,
                "latestVideoID": -1,
                "wasAvailable": False,
                "isAvailable": False,
                "previousError": "",
                "loggedError": False
            }
        self.state[username]["wasLive"] = self.state[username]["isLive"]
        self.state[username]["isLive"] = is_live
        previous_video_id = self.state[username]["latestVideoID"]
        self.state[username]["latestVideoID"] = latest_video_id
        if "isAvailable" in self.state[username]:
            self.state[username]["wasAvailable"] = \
                self.state[username]["isAvailable"]
            self.state[username]["isAvailable"] = is_available
        else:
            self.state[username]["wasAvailable"] = is_available
            self.state[username]["isAvailable"] = is_available
        await self.write_state()
        return previous_video_id

    async def write_state(self):
        with self.state_lock:
            try:
                with open(self.STATE_FILE_PATH, mode='w', encoding='utf-8') as f:
                    f.write(json.dumps(self.state))
            except Exception as e:
                await self.error(f"COULDN'T WRITE TO STATE FILE: {e}")
    
    async def notify_monitor(self, config: dict, username: str, available: bool):
        for user_id, settings in config[username].items():
            if settings[Setting.MONITOR]:
                await self.DM(user_id, f"`@{username}` became "
                              f"{'available' if available else 'unavailable'}! "
                              f"<https://www.tiktok.com/@{username}/>")

    async def notify_live(self, config: dict, username: str):
        for user_id, settings in config[username].items():
            if settings[Setting.LIVES]:
                await self.DM(user_id, f"`@{username}` went LIVE! "
                              f"<https://www.tiktok.com/@{username}/live>")
            if Setting.ALARM in settings and settings[Setting.ALARM]:
                # Will only work for me, on my Windows laptop.
                run("START /B \"C:\\Program Files\\VLC\\vlc\" alarm.ogg",
                    shell=True)

    async def notify_video(self, config: dict, username: str, video_id: int, \
                           video_desc: str):
        # Extremely unlikely to be more than one upload for small use-cases.
        for user_id, settings in config[username].items():
            if settings[Setting.VIDEOS]:
                # If this user has filters configured with it, only send
                # notification if at least one of the words is found in the video's
                # caption.
                if Setting.FILTER in settings:
                    if not any(phrase in video_desc \
                               for phrase in settings[Setting.FILTER]):
                        continue
                await self.DM(user_id, f"New upload from `@{username}`! "
                           f"<https://www.tiktok.com/@{username}/video/{video_id}>")

    async def notify_deleted_video(self, config: dict, username: str, \
                                   video_id: int):
        for user_id, settings in config[username].items():
            if settings[Setting.VIDEOS]:
                await self.DM(user_id, f"`@{username}`'s latest upload "
                        f"<https://www.tiktok.com/@{username}/video/{video_id}> "
                        f"was made unavailable!")
    
    async def DM(self, user_id: str, msg: str):
        user = await self.client.fetch_user(user_id)
        await user.send(msg)
    
    async def error(self, msg: str, error_type: ReasonForFailure=None, username: str=None,
                    group_number: int=None, html_response=None):
        if group_number is not None:
            self.print_char('!', group_number)
        if error_type is not None and username is not None:
            if "previousError" in self.state[username] and \
                self.state[username]["previousError"] == error_type:
                if "loggedError" not in self.state[username] or \
                    ("loggedError" in self.state[username] and \
                    not self.state[username]["loggedError"]):
                    self.state[username]["loggedError"] = True
                    try:
                        channel = await self.client.fetch_channel(self.LOG_CHANNEL)
                        # If a HTML response is provided, write it to a file and attach it.
                        attachment = None
                        if html_response is not None:
                            try:
                                filepath = f"error_{group_number}.html"
                                with open(filepath, mode='w', encoding='utf-8') as f:
                                    f.write(html_response.html)
                                attachment = File(filepath)
                            except: # Couldn't create attachment.
                                self.print_char('?', group_number)
                        await channel.send(content=msg, file=attachment)
                    except Exception as e:
                        # No valid log channel ID, just print it instead.
                        print(msg)
            else:
                self.state[username]["previousError"] = error_type
                self.state[username]["loggedError"] = False
        else:
            try:
                channel = await self.client.fetch_channel(self.LOG_CHANNEL)
                # If a HTML response is provided, write it to a file and attach it.
                attachment = None
                if html_response is not None:
                    try:
                        filepath = f"error_{group_number}.html"
                        with open(filepath, mode='w', encoding='utf-8') as f:
                            f.write(html_response.html)
                        attachment = File(filepath)
                    except: # Couldn't create attachment.
                        self.print_char('?', group_number)
                await channel.send(content=msg, file=attachment)
            except Exception as e:
                # No valid log channel ID, just print it instead.
                print(msg)
