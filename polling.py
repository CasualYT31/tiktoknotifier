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

# Private accounts have this appearing more than once:
# Follow this account to see their contents and likes

from subprocess import run
from time import time as now

import requests
from discord.ext import tasks, commands

from config import get_usernames_and_config, Setting

class PollingCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.username_counter = 0
        # Format:
        # {
        #   "username": {
        #       "previousLive": bool,
        #       "currentLive": bool,
        #       "latestVideoID": int,
        #       "lastWentLive": float
        #   }
        # }
        # Could add loop which cleans up state? Removes stale users?
        self.state = {}
        # Attempt to load cookie. This will open up access to private accounts you
        # can access.
        # You should be able open the Dev Tools in your browser, open TikTok, find
        # the original GET request in the Network tab, copy it as cURL request, and
        # extract the 'cookie' parameter from there.
        self.cookie = ""
        try:
            with open("cookie.txt") as cookie_file:
                self.cookie = cookie_file.read()
        except Exception as e:
            print("Could not read cookie! " + e)
        self.poller.start()

    def cog_unload(self):
        self.poller.cancel()
    
    async def DM(self, user_id: str, msg: str):
        user = await self.client.fetch_user(user_id)
        await user.send(msg)

    async def live_notifications(self, config: dict, username: str):
        for user_id, settings in config[username].items():
            if settings[Setting.LIVES]:
                await self.DM(user_id, f"`@{username}` went LIVE! "
                              f"<https://www.tiktok.com/@{username}/live>")
            if Setting.ALARM in settings and settings[Setting.ALARM]:
                # Will only work for me, on my Windows laptop.
                run("START /B \"C:\\Program Files\\VLC\\vlc\" alarm.ogg",
                    shell=True)

    async def video_notifications(self, config: dict, username: str, video_id: int):
        # Extremely unlikely to be more than one upload for small use-cases.
        for user_id, settings in config[username].items():
            if settings[Setting.VIDEOS]:
                await self.DM(user_id, f"New upload from `@{username}`! "
                           f"<https://www.tiktok.com/@{username}/video/{video_id}>")
    
    def get_request(self, url: str):
        return str(requests.get(f"https://www.tiktok.com/{url}",
                                headers={'Cookie': self.cookie}).content)
    
    def check_if_video_exists(self, username: str, video_id: str) -> bool:
        response = self.get_request(f"@{username}/video/{video_id}")
        # If "Video currently unavailable" occurs more than once in the response,
        # the video is inaccessible.
        return response.count("Video currently unavailable") <= 1

    # This algorithm is fine for a few dozen configured users or so. Not good for
    # large scale work, though. If usernames are added and removed frequently, users
    # could be skipped over frequently, too.
    # https://github.com/carcabot/tiktok-signature/issues/105
    @tasks.loop(seconds=3.0)
    async def poller(self):
        # If there are no configured users, simply wait until there are.
        usernames, config = get_usernames_and_config()
        if len(usernames) == 0:
            return
        
        # Increment username counter, and adjust it if it falls out of range.
        self.username_counter += 1
        if self.username_counter >= len(usernames):
            self.username_counter = 0
        
        # Fire off GET request for the user.
        username = usernames[self.username_counter]
        response = self.get_request(f"@{username}")

        # Is TikTok beginning to deny access? In which case, ignore this request.
        if "Access Denied" in response:
            print(f"Access denied when polling for @{username}!")
            return
        
        # Is this TikTok page private? If so, will need cookies.
        if response.count("Follow this account to see their contents and likes") \
            > 1:
            print(f"@{username} is a private account!")
            return
        
        # Is there not even one /video/ link? If so, something probably went wrong.
        # Sometimes, TikTok will respond with a page that has no video links, or
        # only some of them. No idea why atm...
        if response.count("/video/") == 0:
            print(f"@{username} responded with no videos! Content saved to "
                  "error.html!")
            with open("error.html", 'w') as f:
                f.write(response)
            return
        
        # Add state object for this user if it doesn't already exist.
        if username not in self.state:
            self.state[username] = {
                "previousLive": False,
                "currentLive": False,
                "latestVideoID": -1,
                "lastWentLive": 0.0
            }

        # Store the latest video ID. Always present since we already checked above.
        previous_video_id = self.state[username]["latestVideoID"]
        video_link = response.find("/video/")
        first_quote_after_video = response.find('"', video_link)
        latest_video_id = int(response[video_link+7:first_quote_after_video])

        # If the previous video ID is larger, then either the video became
        # unavailable later, or something went wrong, so need to take a closer look.
        # (See above: sometimes not all video links are returned)...
        if self.state[username]["latestVideoID"] < previous_video_id:
            print(f"@{username} previous video ID "
                    f"{previous_video_id}, latest video ID "
                    f"{self.state[username]['latestVideoID']}.")
            # Does previous video still exist? If so, then the GET request must be
            # ignored and the user's state restored.
            if self.check_if_video_exists(username, previous_video_id):
                print(f"@{username} didn't return proper response, ignoring.")
                with open("error2.html", 'w') as f:
                    f.write(response)
                self.state[username]["latestVideoID"] = previous_video_id
                return
            # If not, then the video was likely removed in some way! Forget the
            # previous video ID.
            print(f"@{username}: previous video is likely no longer available!")
        
        # Manage LIVE status flags.
        self.state[username]["previousLive"] = self.state[username]["currentLive"]
        self.state[username]["currentLive"] = "SpanLiveBadge" in response
        if self.state[username]["previousLive"] and \
            not self.state[username]["currentLive"]:
            print(f"@{username} going offline, content saved to error3.html")
            with open("error3.html", 'w') as f:
                f.write(response)
        
        # If this user went LIVE, send notifications.
        if not self.state[username]["previousLive"] and \
            self.state[username]["currentLive"]:
            # Due to problems with the GET request, occasionally a user's
            # page will be returned without the LIVE badge, despite them being LIVE.
            # This will cause several LIVE notifications to fire off across a
            # singular LIVE, and we need to prevent this. Easiest way is to prevent
            # LIVE notifications being sent for the same user for 2 hours after they
            # last went LIVE.
            current_time = now()
            if current_time - self.state[username]["lastWentLive"] > 7200.0:
                self.state[username]["lastWentLive"] = current_time
                await self.live_notifications(config, username)
            else:
                print(f"@{username} reported as LIVE again in under 2 hours.")

        # If this user uploaded a new video, send notifications.
        # Don't send any if this state is being set for the first time, however.
        if latest_video_id > previous_video_id:
            self.state[username]["latestVideoID"] = latest_video_id
            if previous_video_id >= 0:
                await self.video_notifications(config, username,
                                              self.state[username]["latestVideoID"])
        
        # Single dot means poll succeeded.
        print(".", end='', flush=True)
