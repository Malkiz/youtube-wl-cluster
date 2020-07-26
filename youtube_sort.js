async function load_deps(options = {}) {
	await fetch('https://apis.google.com/js/api.js')
	await delay(500)
	await gapi.load("client:auth2", function() {
		gapi.auth2.init({client_id: options.client_id});
	});
	await authenticate()
	await loadClient(options)
}

function delay(ms) {
	return new Promise(resolve => setTimeout(resolve,ms))
}

async function youtube_sort_malkiz(options) {
	await load_deps(options)
	const ids = [...new Set([...document.querySelectorAll("a[href^='/watch']")].map(e => e.href.match(/v=([^&]*)/)[1]))]
	const data = get_videos_data(ids)
}

async function get_videos_data(ids) {
	const ids_chunks = chunk(ids, 50)
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

function authenticate() {
	return gapi.auth2.getAuthInstance()
		.signIn({scope: "https://www.googleapis.com/auth/youtube.readonly"})
		.then(function() { console.log("Sign-in successful"); },
			function(err) { console.error("Error signing in", err); });
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
			console.log("Response", response);
		},
			function(err) { console.error("Execute error", err); });
}
