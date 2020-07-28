async function load_deps() {
	// await fetch('https://apis.google.com/js/api.js')
	await gapi.load("client");
	await waitFor(() => gapi.client);
	await gapi.client.init({ 'apiKey': localStorage.getItem('api_key') || options.api_key });
	await loadClient();
}

async function waitFor(fn) {
	while(!fn()) { await delay(50) }
}
function delay(ms) {
	return new Promise(resolve => setTimeout(resolve,ms))
}

let options;
async function youtube_sort_malkiz(opts) {
	options = opts;
	await load_deps();
	[...document.getElementsByTagName('ytd-button-renderer')].forEach(e => e.parentNode.removeChild(e));
	const ids_arr = [...document.querySelectorAll("a[href^='/watch']")].map(e => e.href.match(/v=([^&]*)/)[1]);
	const ids = [...new Set(ids_arr)]
	console.log(`Found ${ids.length} video ids`);
	const data = await get_videos_data(ids);
	console.log('getting categories list');
	const cats = await categories();
	console.log('mapping category names');
	data.forEach(d => {
		d.index = ids_arr.findIndex(id => id == d.id);
		d.duration = d.contentDetails.duration.replace(/[^\d]+/g, ':').replace(/^:|:$/g, '')
		const category = cats.find(c => c.id == d.snippet.categoryId);
		d.category = category && category.snippet.title;
	});
	window.videos_for_print = data;
	console.log('printing results');
	console.log(data);
	print(data);
}

function categories() {
	return gapi.client.youtube.videoCategories.list({
		"part": [
			"snippet"
		],
		"regionCode": "US"
	})
		.then(function(response) {
			return response.result.items
		},
			function(err) { console.error("Execute error", err); });
}

const values = {
	index: video => video.index,
	category: video => video.category,
	published: video => video.snippet.publishedAt,
	channel: video => video.snippet.channelTitle
}
const sorters = {
	index: (a, b) => str_sort(a.index, b.index),
	category: (a, b) => str_sort(a.category, b.category),
	published: (a, b) => str_sort(new Date(a.snippet.publishedAt), new Date(b.snippet.publishedAt)),
	channel: (a, b) => str_sort(a.snippet.channelTitle, b.snippet.channelTitle)
}
const orders = [['index'], ['category', 'published', 'channel'], ['category', 'channel', 'published']]
let order_index = 0;

function vid_sort(a, b) {
	const o = orders[order_index];
	let res
	for (i = 0; i < o.length; i++) {
		res = sorters[o[i]](a,b)
		if (res) return res
	}
	return res
}

function str_sort(a, b) {
	if (a > b) return 1;
	if (a < b) return -1;
	return 0;
}

async function get_videos_data(ids) {
	const ids_chunks = chunk(ids, 50)
	console.log(`getting data in ${ids_chunks.length} chunks`)
	const promises = ids_chunks.map(chunk => execute(chunk))
	const results = await Promise.all(promises)
	return join_concat(results)
}

function chunk(arr, n=50) {
	var i,l,temparray,chunks=[];
	for (i=0,l=arr.length; i<l; i+=n) {
		temparray = arr.slice(i,i+n);
		chunks.push(temparray)
	}
	return chunks
}

function join_concat(arrs) {
	return arrs.reduce((a, item) => a.concat(item), [])
}

function loadClient() {
	gapi.client.setApiKey(localStorage.getItem('api_key') || options.api_key);
	return gapi.client.load("https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest")
		.then(function() { console.log("GAPI client loaded for API"); },
			function(err) { console.error("Error loading GAPI client for API", err); });
}

function execute(ids = []) {
	return gapi.client.youtube.videos.list({
		"part": [
			"snippet,contentDetails,statistics,topicDetails"
		],
		"id": [ ids.join(',') ]
	})
		.then(function(response) {
			return response.result.items
		},
			function(err) { console.error("Execute error", err); })
}

window.resort = function resort(videos) {
	order_index = (order_index + 1) % orders.length;
	document.getElementById('sort').value = order_index;
	print(videos)
}

function print(videos, play_first = true) {
	console.log('sorting');
	const sorted = window.videos_for_print = Array.from(videos).sort(vid_sort);
	const o = orders[order_index]

	const table = `
		<table style="color: hsl(0, 0%, 6.7%); font-family: Roboto, Arial, sans-serif; border-spacing: 1em;">
		<thead>
		<tr>
		<th></th>
		<th onclick="resort(window.videos_for_print)" style="cursor: pointer; border-bottom: 1px solid;">#</th>
		${Object.keys(values).map(s => `<th>${s}</th>`).join('\n')}
		<th>duration</th>
		<th></th>
		<th>Video</th>
		</tr>
		</thead>
		<tbody>
		${sorted.map((video, index) => `
			<tr style="padding: 1em;" id="row_${index}">
			<td onclick="window.remove_video('${video.id}')" style="cursor: pointer; border-bottom: 1px solid;">x</td>
			<td style="color: hsla(0, 0%, 6.7%, .6);">${index + 1}</td>
			${Object.keys(values).map(s => `<td>${values[s](video)}</td>`).join('\n')}
			<td>${video.duration}</td>
			<td><img src="${video.snippet.thumbnails.default.url}" style="cursor: pointer;" onclick="window.play_index(${index})"></td>
			<td>${youtubeLink(video.id, video.snippet.localized.title)}</a></td>
			</tr>
			`).join("\n")}
		</tbody>
		</table>
		`;

	var div = document.getElementById('videos_list_div_malkiz');
	if (!div) {
		const urlParams = new URLSearchParams(window.location.search);
		const html = `
			<div id="player"></div>
			<div>
			<button onclick="window.play_prev()">PREV</button>
			<button onclick="window.play_next()">NEXT</button>
			<button onclick="window.do_like(window.current_id())">LIKE</button>
			<button onclick="window.do_dislike(window.current_id())">DISLIKE</button>
			<button onclick="window.do_unlike(window.current_id())">UNLIKE</button>
			</div>
			<div>
			playlist:
			<input type="text" placeholder="playlist" value="${urlParams.get('list') || ''}" id="playlist-id"/>
			<button onclick="window.remove_current()">REMOVE</button>
			</div>
			<div>
			sort:
			<select name="sort" id="sort">
			${orders.map((o,i) => `<option value="${i}">${o.join(',')}</option>`).join('\n')}
			</select>
			</div>
			<script></script>
			<div id="videos_list_div_malkiz" style="overflow-y: scroll; height:800px;">
			${table}
			</div>
			`;

		document.write(html);
		document.close();

		document.querySelector('#sort').addEventListener('change', (event) => {
			order_index = Number(event.target.value)
			print(window.videos_for_print)
		})

		player()
	} else {
		div.innerHTML = table
		if (play_first) window.play_index(0)
	}
}

function youtubeLink(videoId, children) {
	return `<a href="/watch?v=${videoId}" target="_blank">${children}</a>`;
}

let curr_video_index = 0;

function player() {
	var tag = document.createElement('script');

	tag.src = "https://www.youtube.com/iframe_api";
	var firstScriptTag = document.getElementsByTagName('script')[0];
	firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

	var player;
	window.onYouTubeIframeAPIReady = function onYouTubeIframeAPIReady() {
		player = new YT.Player('player', {
			height: '390',
			width: '640',
			videoId: current_id(),
			events: {
				'onReady': onPlayerReady,
				'onStateChange': onPlayerStateChange
			}
		});
	}
	function onPlayerReady(event) {
		event.target.playVideo();
	}
	function onPlayerStateChange(event) {
		console.log('player state changed:', event.data)
		switch (event.data) {
			case YT.PlayerState.ENDED:
				prompt_like()
				remove_current()
				break;
			case YT.PlayerState.UNSTARTED:
				player.playVideo()
				break;
		}
	}
	function stopVideo() {
		console.log('stopping video')
		player.stopVideo();
	}
	window.play_next = function play_next() {
		play_index(curr_video_index + 1)
	}
	window.play_prev = function play_prev() {
		play_index(curr_video_index - 1)
	}
	window.play_index = function play_index(index) {
		curr_video_index = index;
		player.loadVideoById(current_id(), 0)
		const row = document.getElementById(`row_${index}`)
		const topPos = row.offsetTop;
		document.getElementById('videos_list_div_malkiz').scrollTop = topPos;
		document.getElementById('player').scrollIntoView()
	}
	window.remove_current = function remove_current() {
		const success = remove_video(current_id())
		if (success) play_index(curr_video_index);
		else play_next()
	}
	function prompt_like() {
		const ans = prompt("Did you like the video? y = like, n = dislike, c = clear, empty = do nothing", '')
		const id = current_id();
		switch(ans.toLowerCase()) {
			case 'y': return do_like(id);
			case 'n': return do_dislike(id);
			case 'c': return do_unlike(id);
		}
	}
}

window.current_id = function current_id() {
	return window.videos_for_print[curr_video_index].id
}

window.remove_video = function remove_video(id) {
	const len = window.videos_for_print.length;
	window.videos_for_print = window.videos_for_print.filter(v => v.id != id);
	print(window.videos_for_print, false);
	remove_video_from_playlist(id);
	return window.videos_for_print.length != len;
}

function remove_video_from_playlist(id) {
	const playlist = document.getElementById('playlist-id').value;
	if (!playlist) {
		console.log('enter a playlist ID in order to automatically remove videos');
		return;
	}
	const data = {"context":{"client":{"hl":"en","gl":"IL","visitorData":"","userAgent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0,gzip(gfe)","clientName":"WEB","clientVersion":"2.20200724.05.01","osName":"Windows","osVersion":"10.0","browserName":"Firefox","browserVersion":"78.0","screenWidthPoints":863,"screenHeightPoints":722,"screenPixelDensity":1,"utcOffsetMinutes":180,"userInterfaceTheme":"USER_INTERFACE_THEME_DARK"},"request":{"sessionId":"0","internalExperimentFlags":[],"consistencyTokenJars":[]},"user":{},"clientScreenNonce":"","clickTracking":{"clickTrackingParams":""}},"actions":[{"action":"ACTION_REMOVE_VIDEO_BY_VIDEO_ID","removedVideoId":id}],"playlistId":playlist};
	const url = 'https://www.youtube.com/youtubei/v1/browse/edit_playlist?key=' + ytcfg.get('INNERTUBE_API_KEY')
	do_post(url, data)
}

window.do_like = function do_like(id) {
	return like_url('https://www.youtube.com/youtubei/v1/like/like?key=', id)
}

window.do_dislike = function do_dislike(id) {
	return like_url('https://www.youtube.com/youtubei/v1/like/dislike?key=', id)
}

window.do_unlike = function do_unlike(id) {
	return like_url('https://www.youtube.com/youtubei/v1/like/removelike?key=', id)
}

function like_url(url, id) {
	url += ytcfg.get('INNERTUBE_API_KEY')
	const data = {"context":{"client":{"hl":"en","gl":"IL","visitorData":"","userAgent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0,gzip(gfe)","clientName":"WEB","clientVersion":"2.20200724.05.01","osName":"Windows","osVersion":"10.0","browserName":"Firefox","browserVersion":"78.0","screenWidthPoints":874,"screenHeightPoints":722,"screenPixelDensity":1,"utcOffsetMinutes":180,"userInterfaceTheme":"USER_INTERFACE_THEME_DARK"},"request":{"sessionId":"0","internalExperimentFlags":[],"consistencyTokenJars":[{"encryptedTokenJarContents":"","expirationSeconds":"600"}]},"user":{},"clientScreenNonce":"","clickTracking":{"clickTrackingParams":""}},"target":{"videoId":id},"params":""};
	do_post(url, data)
}
function do_post(url, data) {
	return fetch(url, {
		method : "POST",
		body: JSON.stringify(data),
		headers: new Headers({Authorization: localStorage.getItem('malkiz_youtube_authorization') || options.authorization})
	}).then(response => JSON.parse(response.text()))
		.then(
			json => console.log(json.status)
		);
}
