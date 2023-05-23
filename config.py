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

"""Code related to reading from and writing to configuration."""

from threading import Lock
from enum import StrEnum
import json

class Setting(StrEnum):
    """The keys used for the settings stored in the configuration."""

    VIDEOS = "videos"
    LIVES = "lives"

"""Lock used to guard access to the configuration."""
__CONFIG_LOCK = Lock()

"""Lock used to guard access to the configuration file."""
__CONFIG_FILE_LOCK = Lock()

"""Path to the configuration file."""
__CONFIG_FILE_PATH = "./config.json"

"""Cache of the configuration."""
try:
    with open(__CONFIG_FILE_PATH, 'r') as f:
        global __CONFIG_CACHE
        __CONFIG_CACHE = json.loads(f.read())
except Exception as e:
    print(f"COULDN'T READ FROM CONFIG FILE: {e}")

def __write_config():
    global __CONFIG_CACHE
    with __CONFIG_FILE_LOCK:
        try:
            with open(__CONFIG_FILE_PATH, 'w') as f:
                f.write(json.dumps(__CONFIG_CACHE))
        except Exception as e:
            print(f"COULDN'T WRITE TO CONFIG FILE: {e}")

def update_setting(username: str, user_id: str, setting: str, value):
    global __CONFIG_CACHE
    with __CONFIG_LOCK:
        if username not in __CONFIG_CACHE:
            __CONFIG_CACHE[username] = {}
        if user_id not in __CONFIG_CACHE[username]:
            __CONFIG_CACHE[username][user_id] = {}
        __CONFIG_CACHE[username][user_id][setting] = value
        __write_config()

def delete_discord_user(username: str, user_id: str):
    global __CONFIG_CACHE
    with __CONFIG_LOCK:
        if username in __CONFIG_CACHE and user_id in __CONFIG_CACHE[username]:
            del __CONFIG_CACHE[username][user_id]
            if not __CONFIG_CACHE[username]:
                del __CONFIG_CACHE[username]
        __write_config()

def get_all_users_for_discord_user(user_id: str):
    global __CONFIG_CACHE
    # On small scales, this is fine. But on larger scales, it would be better if
    # the user_id -> username mapping was cached separately.
    return_dict = {}
    with __CONFIG_LOCK:
        for username in __CONFIG_CACHE:
            for discord_user_id, settings in __CONFIG_CACHE[username].items():
                if user_id == discord_user_id:
                    return_dict[username] = settings
    return return_dict

def get_user_for_discord_user(username: str, user_id: str):
    global __CONFIG_CACHE
    with __CONFIG_LOCK:
        if username in __CONFIG_CACHE and user_id in __CONFIG_CACHE[username]:
            return __CONFIG_CACHE[username][user_id]
    return {}

def get_text_for_settings(videos: bool, lives: bool):
    if videos and lives:
        return "videos and lives"
    elif videos:
        return "videos"
    elif lives:
        return "lives"
