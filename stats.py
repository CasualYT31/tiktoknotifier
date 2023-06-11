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

from time import time
from datetime import datetime
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

def time_as_str(time_to_convert=None) -> str:
    if time_to_convert is None: time_to_convert = time()
    return datetime.fromtimestamp(time_to_convert).strftime('%Y-%m-%d %H:%M:%S')

def __reset_stats():
    global __STATS_CACHE
    __STATS_CACHE = {}
    try:
        with open("last-reset-stats-at.txt", mode='w', encoding='utf-8') as f:
            f.write(time_as_str())
    except Exception as e:
        print(f"COULD NOT WRITE last-reset-stats-at.txt: {e}")
    with __STATS_LATEST_POLL_LOCK:
        try:
            with open("latest-poll-result.txt", mode='w', encoding='utf-8') as f:
                pass
        except Exception as e:
            print(f"COULDN'T CLEAR latest-poll-result.txt: {e}")

global __STATS_LATEST_POLL_LOCK
__STATS_LATEST_POLL_LOCK = Lock()

def __write_latest_poll(username: str, latest_poll: str):
    """You must have previously acquired the __STATS_LOCK!"""

    __STATS_CACHE[username]["last-poll"] = latest_poll
    last_poll_at = time_as_str()
    __STATS_CACHE[username]["last-poll-at"] = last_poll_at
    with __STATS_LATEST_POLL_LOCK:
        try:
            with open("latest-poll-result.txt", mode='w', encoding='utf-8') as f:
                f.write(f"`@{username}`: {latest_poll}, at {last_poll_at}")
        except Exception as e:
            print(f"COULDN'T UPDATE latest-poll-result.txt WITH {latest_poll}: {e}")

def __read_latest_poll() -> str:
    with __STATS_LATEST_POLL_LOCK:
        try:
            with open("latest-poll-result.txt", mode='r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"COULDN'T READ latest-poll-result.txt WITH: {e}")
            return "<error reading latest-poll-result.txt>"

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
        },
        "last-poll": "N/A",
        "last-poll-at": "N/A"
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
        __write_latest_poll(username, "Success")
        __write_stats()

def record_failed_poll(username: str, reason: ReasonForFailure,
                       error_div: str=None):
    with __STATS_LOCK:
        __add_user(username)
        if error_div is None:
            __STATS_CACHE[username]["failure"][reason] += 1
            latest_poll = reason.replace('-', ' ').title()
        else:
            if error_div in __STATS_CACHE[username]["failure"] \
                [ReasonForFailure.UNKNOWN_ERROR_DIV]:
                __STATS_CACHE[username]["failure"] \
                    [ReasonForFailure.UNKNOWN_ERROR_DIV][error_div] += 1
            else:
                __STATS_CACHE[username]["failure"] \
                    [ReasonForFailure.UNKNOWN_ERROR_DIV][error_div] = 1
            latest_poll = error_div
        __write_latest_poll(username, latest_poll)
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
    # Make copy so as not to lock up the rest of the bot.
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
        failure_counters = {}
        for stats in stats_copy.values():
            for failure_reason, count in stats["failure"].items():
                if failure_reason == ReasonForFailure.UNKNOWN_ERROR_DIV:
                    for div_str, inner_count in count.items():
                        if failure_reason not in failure_counters:
                            failure_counters[failure_reason] = {}
                        if div_str in failure_counters:
                            failure_counters[failure_reason][div_str] += inner_count
                        else:
                            failure_counters[failure_reason][div_str] = inner_count
                elif count > 0:
                    if failure_reason in failure_counters:
                        failure_counters[failure_reason] += count
                    else:
                        failure_counters[failure_reason] = count
        for failure_reason, count in failure_counters.items():
            if failure_reason == ReasonForFailure.UNKNOWN_ERROR_DIV:
                for div_str, inner_count in count.items():
                    caption = div_str.title()
                    msg += f"Unknown Error Div: {caption}: {inner_count}\n"
            elif count > 0:
                caption = failure_reason.replace("-", " ").title()
                msg += f"{caption}: {count}\n"
        failures = sum([sum([fail_stats for reason, fail_stats in
                         stats["failure"].items() if
                         reason != ReasonForFailure.UNKNOWN_ERROR_DIV] +
                        [unknown_fail_stats for unknown_fail_stats in
                    stats["failure"][ReasonForFailure.UNKNOWN_ERROR_DIV].values()])
                    for stats in stats_copy.values()])
        msg += f"Total Failures: {failures}\n"
        msg += f"Total Polls: {successful + failures}\n"
        msg += "Success Rate: {:.2f}%\n".format(
            successful / (successful + failures) * 100.0)
    else:
        # Summarise user's stats.
        msg += f"**__{username}'s Polling Stats__**\n"
        if username not in stats_copy:
            msg += f"None."
        else:
            successful = stats_copy[username]['success']
            total = successful
            msg += f"Successful: {total}\n"
            for failure_reason, count in stats_copy[username]["failure"].items():
                if failure_reason == ReasonForFailure.UNKNOWN_ERROR_DIV:
                    for div_str, inner_count in count.items():
                        caption = div_str.title()
                        total += inner_count
                        msg += f"Unknown Error Div: {caption}: {inner_count}\n"
                elif count > 0:
                    caption = failure_reason.replace("-", " ").title()
                    total += count
                    msg += f"{caption}: {count}\n"
            msg += f"Total Failures: {total - successful}\n"
            msg += f"Total Polls: {total}\n"
            msg += "Success Rate: {:.2f}%\n".format(successful / total * 100)
            if "last-poll" not in stats_copy[username]:
                stats_copy[username]['last-poll'] = "Unknown"
            msg += f"Last Poll: {stats_copy[username]['last-poll']}\n"
            if "last-poll-at" not in stats_copy[username]:
                stats_copy[username]['last-poll-at'] = "Unknown"
            msg += f"Last Polled At: {stats_copy[username]['last-poll-at']}\n"
    msg += "**__Generic Polling Stats__**\n"
    msg += "Last Reset At: "
    try:
        with open("last-reset-stats-at.txt", mode='r', encoding='utf-8') as f:
            msg += f.read()
    except Exception as e:
        print(f"COULD NOT READ last-reset-stats-at.txt: {e}")
        msg += "<unknown>"
    msg += f"\nLatest Poll: {__read_latest_poll()}"
    return msg 
