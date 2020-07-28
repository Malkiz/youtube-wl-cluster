This repo is divided into 2 parts: ML research (implemented in python) and a functional tool for managing YouTube (implemented in javascript).

# Research (python)
The goal of this research is to take a list of YouTube videos and cluster them into groups. The groups are determined by the data YouTube exposes about the videos.

## Getting the initial playlist data
0. make sure you have the file `apiKey.json` that looks like this:
```
{"key":"<youtube-api-key>"}
```
1. Login to YouTube
2. Go to https://www.youtube.com/playlist?list=WL
3. Scroll all the way to the bottom of the page. Do this until the entire list is loaded to the page.
4. Open the browser console (F12) and run this script:
```javascript
["id", ...([...document.querySelectorAll('ytd-playlist-video-renderer.style-scope > div:nth-child(2) > a:nth-child(1)')].map(e => e.href.match(/v=([^&]*)/)[1]))].join('\n')
```
5. Copy the output to a text file and save it as `WL.csv`. The file should look like this:
```
id
W6nsrjAxO3Y
ewtgUFSMsnY
4WR8Qvsv70s
```
Each line is an identifier of a single youtube video.

## Setup env

### First time
1. Install dependencies
```
sudo apt-get install python3-venv python3-tk
```
2. Create and activate env:
```
python3 -m venv py_venv
source py_venv/bin/activate
```
3. Install packages
```
pip install -r py_freeze.txt
```

### Development
1. activate env
```
source py_venv/bin/activate
```
2. run script
```
python youtube_api.py
```

### Save new python dependencies
1. If you install new dependencies, save them:
```
pip3 freeze > py_freeze.txt
```
2. git commit

### Close the dev env
```
deactivate
```

# YouTube sort & manage
This is a javascript tool that is meant to "control" YouTube playlists in a more intuitive and easy way.

## Features
- Sort the playlist by different values (category, channel, publish time, etc).
- Automatically remove the video from the playlist after watching (useful for the Watch Later playlist)
- Automatically ask the user to like/dislike/unlike the video after watching it. The "likes" affect the YouTube algorithm for reccomending and notifying the user about new videos. So avid users should care about managing their liked videos.

## Installation
- Create a new bookmark and paste into it the code from `bookmarklet.js`
- Set the `api_key` and `authorization`:
  - Option 1: change the code in the bookmarklet to have these values: `youtube_sort_malkiz({api_key: '', authorization: ''})`
  - Option 2: set these values in localStorage: `localStorage.setItem('api_key', ''); localStorage.setItem('malkiz_youtube_authorization', '')`

### api_key
You need to go into Google Console, create an app, and add the `YouTube Data API v3`. Then create an API key for that API, and copy it here.
- Why didn't I provide a key? Because Google has quotas for using their API's and I want to use the free tier. (I developed this as a fun side project, not a commercial tool).
### authorization
- Open your browser's Network tab and make sure it's recording activity.
- Open any video in YouTube and click "like".
- Find the request that was made - it should be have this URL `/youtubei/v1/like/like`
- inspect the request headers and find the `Authorization` header. Copy that value.

## Usage
Open any youtube page and click the bookmark you created. The tool will get all the videos listed in the page and display a new interface for sorting and watching them.
