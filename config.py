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

from numpy import array_split

class Setting(StrEnum):
    """The keys used for the settings stored in the configuration."""

    VIDEOS = "videos"
    LIVES = "lives"
    ALARM = "alarm"
    FILTER = "filter"
    MONITOR = "monitor"

"""Lock used to guard access to the configuration."""
__CONFIG_LOCK = Lock()

"""Lock used to guard access to the configuration file."""
__CONFIG_FILE_LOCK = Lock()

"""Path to the configuration file."""
__CONFIG_FILE_PATH = "./config.json"

"""Cache of the configuration."""
global __CONFIG_CACHE
try:
    with open(__CONFIG_FILE_PATH, mode='r', encoding='utf-8') as f:
        __CONFIG_CACHE = json.loads(f.read())
except Exception as e:
    __CONFIG_CACHE = {}
    print(f"COULDN'T READ FROM CONFIG FILE: {e}")

"""List of the configured usernames. Needs to be a list because I want a defined
order each time it is accessed during execution."""
__CONFIG_USERNAMES = list(__CONFIG_CACHE.keys())

def __write_config():
    global __CONFIG_CACHE
    with __CONFIG_FILE_LOCK:
        try:
            with open(__CONFIG_FILE_PATH, mode='w', encoding='utf-8') as f:
                f.write(json.dumps(__CONFIG_CACHE))
        except Exception as e:
            print(f"COULDN'T WRITE TO CONFIG FILE: {e}")

def update_setting(username: str, user_id: str, setting: str, value):
    global __CONFIG_CACHE
    global __CONFIG_USERNAMES
    with __CONFIG_LOCK:
        if username not in __CONFIG_CACHE:
            __CONFIG_CACHE[username] = {}
            __CONFIG_USERNAMES.append(username)
        if user_id not in __CONFIG_CACHE[username]:
            __CONFIG_CACHE[username][user_id] = {}
        __CONFIG_CACHE[username][user_id][setting] = value
        __write_config()

def delete_setting(username: str, user_id: str, setting: str):
    global __CONFIG_CACHE
    global __CONFIG_USERNAMES
    with __CONFIG_LOCK:
        if username not in __CONFIG_CACHE:
            __CONFIG_CACHE[username] = {}
            __CONFIG_USERNAMES.append(username)
        if user_id not in __CONFIG_CACHE[username]:
            __CONFIG_CACHE[username][user_id] = {}
        if setting in __CONFIG_CACHE[username][user_id]:
            del __CONFIG_CACHE[username][user_id][setting]
        if not __CONFIG_CACHE[username][user_id]:
            del __CONFIG_CACHE[username][user_id]
            if not __CONFIG_CACHE[username]:
                del __CONFIG_CACHE[username]
                __CONFIG_USERNAMES.remove(username)
        __write_config()

def delete_discord_user(username: str, user_id: str):
    global __CONFIG_CACHE
    global __CONFIG_USERNAMES
    with __CONFIG_LOCK:
        if username in __CONFIG_CACHE and user_id in __CONFIG_CACHE[username]:
            del __CONFIG_CACHE[username][user_id]
            if not __CONFIG_CACHE[username]:
                del __CONFIG_CACHE[username]
                __CONFIG_USERNAMES.remove(username)
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

def get_usernames_and_config():
    global __CONFIG_CACHE
    global __CONFIG_USERNAMES
    with __CONFIG_LOCK:
        return (__CONFIG_USERNAMES.copy(), __CONFIG_CACHE.copy())

def get_username_group_and_config(group_number: int, group_count: int):
    assert group_count >= 1
    assert group_number >= 0 and group_number < group_count
    global __CONFIG_CACHE
    global __CONFIG_USERNAMES
    with __CONFIG_LOCK:
        username_groups = array_split(__CONFIG_USERNAMES.copy(), group_count)
        return (username_groups[group_number].tolist(), __CONFIG_CACHE.copy())

def find_group_of_username(username: str, group_count: int) -> tuple:
    assert group_count >= 1
    for group_number in range(group_count):
        username_group, _ = get_username_group_and_config(group_number, group_count)
        if username in username_group:
            return group_number, username_group.index(username), len(username_group)
    return None, None, None

def get_text_for_settings(videos: bool, lives: bool, monitor: bool):
    if monitor:
        return "account status"
    elif videos and lives:
        return "videos and lives"
    elif videos:
        return "videos"
    elif lives:
        return "lives"
