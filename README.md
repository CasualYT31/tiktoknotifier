# tiktoknotifier
This is a Discord bot that polls configured TikTok user pages to see if they have submitted new uploads or gone live, and notify relevant users via Direct Message.

## Dependencies
This bot requires Python 3.11 or later due to use of `StrEnum`.
You will need to install `discord.py`, `numpy`, `requests`, and `requests_html` to run this code.

## Token
In order to run this bot via a Discord application, you will have to create a new text file called `token.txt`, save it in the same folder as `main.py` (or from wherever you are running the bot), and paste your bot's token on the first line.

## Intents
You will also need to grant your application the `Message Content Intent`.

## Owner
In the same folder as `token.txt`, you will also need to create a file called `owner.txt`, which should contain the user ID of the maintainer of the bot. This user will be allowed to submit admin commands such as `?alarm`.

## Log Channel
In the same folder as `token.txt` and `owner.txt`, another file called `log_channel.txt` should be written. This file should contain the ID of the channel which the bot should write logs to. If no file exists, or the ID is invalid, logs will be printed instead.

## Cookies
In order to open up access to private accounts you can access, you will need to provide cookies to the bot. This can be done by carrying out the following:

1. Open your favourite browser, and visit TikTok. Make sure you're logged in.
2. Open the browser's developer tools, open up the Network tab, then refresh the page.
3. You will need to find the correct GET request. For example, if you visited `www.tiktok.com/en`, then the GET request will be for `/en`.
4. Right click this GET request, and select `Copy as cURL`. It may be hidden within a `Copy` submenu.
5. Create a new file in the same folder as `token.txt`, called `cookie.txt`, and paste the request in.
6. There should be a field called `cookie` in the command. Leave the `cookie.txt` file such that it only contains the value of this field (without the `"cookie": ` key, or the quotes and escape characters that surround the value). Save it.
