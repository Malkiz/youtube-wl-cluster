async function load_deps(options = {}) {
	// await fetch('https://apis.google.com/js/api.js')
	await gapi.load("client");
	await waitFor(() => gapi.client);
	await gapi.client.init({ 'apiKey': options.api_key });
	await loadClient(options);
}

async function waitFor(fn) {
	while(!fn()) { await delay(50) }
}
function delay(ms) {
	return new Promise(resolve => setTimeout(resolve,ms))
}

async function youtube_sort_malkiz(options) {
	await load_deps(options)
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

const sorters = {
	category: (a, b) => str_sort(a.category, b.category),
	published: (a, b) => str_sort(new Date(a.snippet.publishedAt), new Date(b.snippet.publishedAt)),
	channel: (a, b) => str_sort(a.snippet.channelTitle, b.snippet.channelTitle)
}
const orders = [['category', 'published', 'channel'], ['category', 'channel', 'published']]
let order_index = 0;

function vid_sort(a, b) {
	const o = orders[order_index];
	for (i = 0; i < o.length; i++) {
		let res = sorters[o[i]](a,b)
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

function loadClient(options) {
	gapi.client.setApiKey(options.api_key);
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

function print(videos) {
	console.log('sorting');
	const sorted = Array.from(videos).sort((a, b) => vid_sort(a, b));

	const html = `
		<table style="color: hsl(0, 0%, 6.7%); font-family: Roboto, Arial, sans-serif; border-spacing: 1em;">
		<thead>
		<tr>
		<th onclick="resort(window.videos_for_print)" style="cursor: pointer; border-bottom: 1px solid;">#</th>
		<th>category</th>
		<th>date</th>
		<th>channel</th>
		<th></th>
		<th>Video</th>
		</tr>
		</thead>
		<tbody>
		${sorted.map((video, index) => `
			<tr style="padding: 1em;">
			<td style="color: hsla(0, 0%, 6.7%, .6);">${index + 1}</td>
			<td>${video.category}</td>
			<td>${video.snippet.publishedAt}</td>
			<td>${video.snippet.channelTitle}</td>
			<td>${youtubeLink(video.id, `<img src="${video.snippet.thumbnails.default.url}">`)}</td>
			<td>${youtubeLink(video.id, video.snippet.localized.title)}</a></td>
			</tr>
			`).join("\n")}
		</tbody>
		</table>
		`;

	document.write(html);
	document.close();
}

function youtubeLink(videoId, children) {
	return `<a href="/watch?v=${videoId}" target="_blank">${children}</a>`;
}
