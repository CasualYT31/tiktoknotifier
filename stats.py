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

"""Records polling stats."""

from threading import Lock
from enum import StrEnum
import json

class ReasonForFailure(StrEnum):
    """Reasons for a failed poll."""

    ACCESS_DENIED = "access-denied"
    PLEASE_WAIT = "please-wait"
    SOMETHING_WENT_WRONG = "something-went-wrong"
    NO_CONTENT = "no-content"
    PAGE_NOT_AVAILABLE = "page-not-available"
    PRIVATE_ACCOUNT = "private-account"
    UNKNOWN_ERROR_DIV = "unknown-error-div"
    USER_POST_ITEM_LIST = "user-post-item-list"
    USER_POST_ITEM_LIST_DIV = "user-post-item-list-div"
    USER_POST_ITEM = "user-post-item"
    NO_VIDEO_LINK = "no-video-link"
    USER_POST_ITEM_DESC = "user-post-item-desc"
    NO_VIDEO_DESC = "no-video-desc"
    FAULTY_VIDEO_LINK = "faulty-video-link"

global __STATS_LOCK
__STATS_LOCK = Lock()

global __STATS_FILE_PATH
__STATS_FILE_PATH = "./stats.json"

global __STATS_CACHE

def __reset_stats():
    global __STATS_CACHE
    __STATS_CACHE = {}

def __add_user(username: str):
    if username in __STATS_CACHE: return
    __STATS_CACHE[username] = {
        "success": 0,
        "failure": {
            ReasonForFailure.ACCESS_DENIED: 0,
            ReasonForFailure.PLEASE_WAIT: 0,
            ReasonForFailure.SOMETHING_WENT_WRONG: 0,
            ReasonForFailure.NO_CONTENT: 0,
            ReasonForFailure.PAGE_NOT_AVAILABLE: 0,
            ReasonForFailure.PRIVATE_ACCOUNT: 0,
            ReasonForFailure.UNKNOWN_ERROR_DIV: {
                # "Primary Error String": 0
            },
            ReasonForFailure.USER_POST_ITEM_LIST: 0,
            ReasonForFailure.USER_POST_ITEM_LIST_DIV: 0,
            ReasonForFailure.USER_POST_ITEM: 0,
            ReasonForFailure.NO_VIDEO_LINK: 0,
            ReasonForFailure.USER_POST_ITEM_DESC: 0,
            ReasonForFailure.NO_VIDEO_DESC: 0,
            ReasonForFailure.FAULTY_VIDEO_LINK: 0,
        }
    }

try:
    with open(__STATS_FILE_PATH, mode='r', encoding='utf-8') as f:
        __STATS_CACHE = json.loads(f.read())
except Exception as e:
    __reset_stats()
    print(f"COULDN'T READ FROM STATS FILE: {e}")

def __write_stats():
    try:
        with open(__STATS_FILE_PATH, mode='w', encoding='utf-8') as f:
            f.write(json.dumps(__STATS_CACHE))
    except Exception as e:
        print(f"COULDN'T WRITE TO STATS FILE: {e}")

def record_successful_poll(username: str):
    with __STATS_LOCK:
        __add_user(username)
        __STATS_CACHE[username]["success"] += 1
        __write_stats()

def record_failed_poll(username: str, reason: ReasonForFailure,
                       error_div: str=None):
    with __STATS_LOCK:
        __add_user(username)
        if error_div is None:
            __STATS_CACHE[username]["failure"][reason] += 1
        else:
            __STATS_CACHE[username]["failure"] \
                [ReasonForFailure.UNKNOWN_ERROR_DIV][error_div] += 1
        __write_stats()

def reset_stats() -> None:
    with __STATS_LOCK:
        __reset_stats()
        __write_stats()

def remove_user(username: str):
    with __STATS_LOCK:
        if username in __STATS_CACHE:
            del __STATS_CACHE[username]
            __write_stats()

def summarise_stats(username: str="") -> str:
    # Make copy so as not to lock up the rest of the program.
    stats_copy = None
    with __STATS_LOCK:
        stats_copy = __STATS_CACHE.copy()
    msg = ""
    if username is None or len(username) == 0:
        # Summarise entire stats.
        msg += f"**__Polling Stats__**\n"
        msg += f"Currently polling **{len(stats_copy.keys())}** user/s.\n"
        successful = sum([stats["success"] for stats in stats_copy.values()])
        msg += f"Successful: {successful}\n"
        failures = sum([sum([fail_stats for reason, fail_stats in
                         stats["failure"].items() if
                         reason != ReasonForFailure.UNKNOWN_ERROR_DIV] +
                        [unknown_fail_stats for unknown_fail_stats in
                    stats["failure"][ReasonForFailure.UNKNOWN_ERROR_DIV].values()])
                    for stats in stats_copy.values()])
        msg += f"Failures: {failures}\n"
        msg += f"Total Polls: {successful + failures}\n"
        msg += "Success Rate: {:.2f}%".format(
            successful / (successful + failures) * 100.0)
    else:
        # Summarise user's stats.
        msg += f"**__{username}'s Polling Stats__**\n"
        successful = stats_copy[username]['success']
        total = successful
        msg += f"Successful: {total}\n"
        for failure_reason, count in stats_copy[username]["failure"].items():
            if failure_reason == ReasonForFailure.UNKNOWN_ERROR_DIV:
                for div_str, inner_count in count:
                    caption = div_str.title()
                    total += inner_count
                    msg += f"Unknown Error Div: {caption}: {inner_count}\n"
            elif count > 0:
                caption = failure_reason.replace("-", " ").title()
                total += count
                msg += f"{caption}: {count}\n"
        msg += f"Total Failures: {total - successful}\n"
        msg += f"Total Polls: {total}\n"
        msg += "Success Rate: {:.2f}%".format(successful / total * 100)
    return msg
