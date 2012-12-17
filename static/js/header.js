/*
 * The song that is currently playing
 */
var nowplaying = null;

/*
 * True if shuffle mode is activated
 */
var shuffle = true;

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
	//if shuffle is active, load the next song
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
			if (shuffle)
			{
				play_random();
			}
			else
			{
				//destroy the sound playpause-controlobject
				$('#playpause-control').html('Play');
				nowplaying.stop();
				nowplaying.destruct();
				nowplaying = null;
			}
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
		if (shuffle)
		{
			//if shuffle is on, play another song
			play_random();
		}

		//TODO: skip behaviour is undefined if shuffle is off
	});

	$('#shuffle-control').click(function()
	{
		if (shuffle)
		{
			shuffle = false;
			$('#shuffle-control').html('Shuffle is off');
		}
		else
		{
			shuffle = true;
			$('#shuffle-control').html('Shuffle is on');
		}
	});
});
