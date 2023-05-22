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

"""Code related to fetching the token."""

from os import getcwd

def __could_not_read_token(e: Exception=None):
    """Reports a failure to retrieve the bot token to stdout.
    
    Parameters
    ----------
    e : Exception
        Exception containing additional information about what went
        wrong. If `None`, nothing extra will be printed.

    Raises
    ------
    SystemExit
        Always.
    """

    print(f"Could not read token from {getcwd()}/token.txt.")
    if e is not None:
        print(f"Exception: {e}")
    print("Please make sure the bot's token is in the first line of the file!")
    print("Exiting...")
    raise SystemExit

def read_token(path: str="./token.txt"):
    """Reads the bot token from a text file.

    Parameters
    ----------
    path : str
        The path of the token file. Defaults to `./token.txt`.
    
    Raises
    ------
    SystemExit
        If the token could not be read. Additional information will be
        printed to stdout.
    """

    token = ''
    try:
        with open(path) as token_file:
            token = token_file.readline().strip()
    except Exception as e:
        __could_not_read_token(e)
    if token == '':
        __could_not_read_token()
    return token
