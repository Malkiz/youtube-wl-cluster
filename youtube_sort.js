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
	await load_deps()
	const ids = [...new Set([...document.querySelectorAll("a[href^='/watch']")].map(e => e.href.match(/v=([^&]*)/)[1]))]
	console.log(`Found ${ids.length} video ids`);
	const data = await get_videos_data(ids);
	console.log('getting categories list');
	const cats = await categories();
	console.log('mapping category names');
	data.forEach(d => {
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
	category: video => video.category,
	published: video => video.snippet.publishedAt,
	channel: video => video.snippet.channelTitle
}
const sorters = {
	category: (a, b) => str_sort(a.category, b.category),
	published: (a, b) => str_sort(new Date(a.snippet.publishedAt), new Date(b.snippet.publishedAt)),
	channel: (a, b) => str_sort(a.snippet.channelTitle, b.snippet.channelTitle)
}
const orders = [['category', 'published', 'channel'], ['category', 'channel', 'published']]
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
	print(videos)
}

function print(videos, play_first = true) {
	console.log('sorting');
	const sorted = window.videos_for_print = Array.from(videos).sort((a, b) => vid_sort(a, b));
	const o = orders[order_index]

	const table = `
		<table style="color: hsl(0, 0%, 6.7%); font-family: Roboto, Arial, sans-serif; border-spacing: 1em;">
		<thead>
		<tr>
		<th></th>
		<th onclick="resort(window.videos_for_print)" style="cursor: pointer; border-bottom: 1px solid;">#</th>
		${o.map(s => `<th>${s}</th>`).join('\n')}
		<th></th>
		<th>Video</th>
		</tr>
		</thead>
		<tbody>
		${sorted.map((video, index) => `
			<tr style="padding: 1em;" id="row_${index}">
			<td onclick="window.remove_video('${video.id}')">x</td>
			<td style="color: hsla(0, 0%, 6.7%, .6);">${index + 1}</td>
			${o.map(s => `<td>${values[s](video)}</td>`).join('\n')}
			<td><img src="${video.snippet.thumbnails.default.url}" onclick="window.play_index(${index})"></td>
			<td>${youtubeLink(video.id, video.snippet.localized.title)}</a></td>
			</tr>
			`).join("\n")}
		</tbody>
		</table>
		`;

	var div = document.getElementById('videos_list_div_malkiz');
	if (!div) {
		const html = `
			<div id="player"></div>
			<button onclick="window.play_prev()">PREV</button>
			<button onclick="window.play_next()">NEXT</button>
			<button onclick="window.remove_current()">REMOVE</button>
			<input type="text" placeholder="playlist" value="WL" id="playlist-id"/>
			<script></script>
			<div id="videos_list_div_malkiz" style="overflow-y: scroll; height:800px;">
			${table}
			</div>
			`;

		document.write(html);
		document.close();

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
			videoId: window.videos_for_print[curr_video_index].id,
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
		player.loadVideoById(window.videos_for_print[curr_video_index].id, 0)
		const row = document.getElementById(`row_${index}`)
		const topPos = row.offsetTop;
		document.getElementById('videos_list_div_malkiz').scrollTop = topPos;
	}
	window.remove_current = function remove_current() {
		const success = remove_video(window.videos_for_print[curr_video_index].id)
		if (success) play_index(curr_video_index);
		else play_next()
	}
}

function remove_video(id) {
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
	fetch(url, {
		method : "POST",
		body: JSON.stringify(data),
		headers: new Headers({Authorization: localStorage.getItem('malkiz_youtube_authorization') || options.authorization})
	}).then(response => JSON.parse(response.text()))
		.then(
			json => console.log(json.status)
		);
}
