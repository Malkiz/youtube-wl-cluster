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
1. Install `venv`
```
sudo apt-get install python3-venv
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
