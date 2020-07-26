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
	console.log('sorting');
	const sorted = data.sort((a, b) => str_sort(a.category, b.category));
	console.log('printing results');
	console.log(sorted);
	print(sorted);
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

function print(videos) {
	const sorted = Array.from(videos)

	const html = `
		<table style="color: hsl(0, 0%, 6.7%); font-family: Roboto, Arial, sans-serif; border-spacing: 1em;">
		<thead>
		<tr>
		<th></th>
		<th style="cursor: pointer; border-bottom: 1px solid;">category</th>
		<th></th>
		<th>Video</th>
		</tr>
		</thead>
		<tbody>
		${sorted.map((video, index) => `
			<tr style="padding: 1em;">
			<td style="color: hsla(0, 0%, 6.7%, .6);">${index + 1}</td>
			<td>${video.category}</td>
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
