## Getting the initial playlist data
1. Login to YouTube
2. Go to https://www.youtube.com/playlist?list=WL
3. Scroll all the way to the bottom of the page. Do this until the entire list is loaded to the page.
4. Open the browser console (F12) and run this script:
```javascript
[...document.querySelectorAll('ytd-playlist-video-renderer.style-scope > div:nth-child(2) > a:nth-child(1)')].map(e => e.href.match(/v=([^&]*)/)[1]).join(',\n')
```
5. Copy the output to a text file and save it. The file should look like this:
```
W6nsrjAxO3Y,
ewtgUFSMsnY,
4WR8Qvsv70s,
```
Each line is an identifier of a single youtube video.

