/*
 * The song that is currently playing
 */
var nowplaying = null;

/*
 * Loads the specified uri and dumps the contents into #main
 */
function load_content(url)
{
	$.get(url, function(data)
	{
		$('#main').html(data)
	});
}

/*
 * Plays a random song from the library
 */
function play_random() {
	$.get('/api/tracks/random', function(data)
	{
		play_song(data['stream_uri']);
	});
}

/*
 * Plays the specified song
 */
function play_song(url) {
	if (nowplaying != null) {
		nowplaying.stop();
		nowplaying.destruct();
	}

	//TODO: once multiple audio formats are supported, query SoundManager2 for the
	//		browser's supported formats and dynamically request the appropriate one.

	nowplaying = soundManager.createSound({
		autoLoad: true,
		autoPlay: true,
		id: 'nowplaying',
		type: 'audio/ogg',
		url: url,
		onfinish: function() {
			play_random();
		},
		onpause: function() {
			$('#playpause-control').html('Play');
		},
		onplay: function() {
			$('#playpause-control').html('Pause');
		},
		onresume: function() {
			$('#playpause-control').html('Pause');
		},
		onstop: function() {
			$('#playpause-control').html('Play');
		}
	});
}

$(document).ready(function()
{
	//configure SoundManager2
	soundManager.audioFormats = {
		//at this time, we only need support for ogg vorbis audio streams.
		'ogg': {
			'type': ['audio/ogg; codecs=vorbis'],
			'required': true
		}
	};
	soundManager.setup({
		url: '/static/swf/',
		onready: function() {
			//once we're ready to go, show the play/pause button
			$('#player').show("slow");
		},
		ontimeout: function(status) {
			//holy crap it broke!
			alert("Failed to load SoundManager2! Status is " + status.success + ", error type is " + status.error.type);
		}
	});

	//set up player controls
	$('#playpause-control').click(function()
	{
		if (nowplaying == null)
		{
			//if the player is stopped, start playing a random song
			play_random();
		}
		else
		{
			//if a sound has been loaded, toggle between playing and paused states
			soundManager.togglePause('nowplaying');
		}
	});

	$('#skip-control').click(function() {
		play_random();
	});
});
