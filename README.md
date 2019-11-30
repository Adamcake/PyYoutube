# PyYoutube
Python 3 wrapper for certain parts of the YouTube API.

## What parts?
Mainly searching and reporting videos. I have an obligation to spend some time removing spam videos from YouTube, which is an easily batch-automated process. I created this wrapper for easier automation of those tasks. If you need any similar endpoints adding, feel free to add them and open a pull request.

## Building
It's just one file, so clone it anywhere you like and then import it. You'll need oauth2client and httplib2 as dependencies. Both are available through pip.  
`pip install oauth2client`  
`pip install httplib2`  
To use the wrapper, you'll need to get yourself a [YouTube Data API key](http://console.developers.google.com/) first, then create a credentials file which will be used to authorize your API requests. youtube.py assumes this file is called "credentials.dat" and will not load if no such file is present.

## Why did you upload this?
In case anyone else in a similar position to me ever wants to automate search-and-report. But it's also here so that I can show potential employers that I have some Python experience. If you're a potential employer: Hello! Please hire me.
