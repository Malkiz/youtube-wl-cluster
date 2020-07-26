javascript:(function() {
	fetch('https://raw.githubusercontent.com/Malkiz/youtube-wl-cluster/master/youtube_sort.js', { cache: 'reload' })
	.then(res => res.text())
	.then(script => {
		eval(script);
		return youtube_sort_malkiz({client_id: '', api_key: ''})
	})
	.catch(e => {
		console.error(e);
		document.write(`Something went wrong, please refer to <a href='https://github.com/Malkiz/youtube-wl-cluster'>script homepage</a> for the latest updates.`);
		document.close();
	})
})();
