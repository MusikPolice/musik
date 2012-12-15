/*
 * The song that is currently playing
 */
var nowplaying = null;

/*
 * True if shuffle mode is activated
 */
var shuffle = true;

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
				//if shuffle is active, load the next song
				$.get('/api/tracks/random', function(data)
				{
					play_song(data['stream_uri']);
				});
			}
			else
			{
				//destroy the sound object
				nowplaying.stop();
				nowplaying.destruct();
				nowplaying = null;
			}
		},
		onfinish: function() {
			$('#playpause').html('Play');
		}
		onpause: function() {
			$('#playpause').html('Play');
		},
		onplay: function() {
			$('#playpause').html('Pause');
		},
		onresume: function() {
			$('#playpause').html('Pause');
		},
		onstop: function() {
			$('#playpause').html('Play');
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
	$('#playpause').click(function()
	{
		if (nowplaying == null)
		{
			//if the player is stopped, start playing the default song
			//TODO: defaults suck.
			play_song('http://localhost:8080/api/stream/track/1');
		}
		else
		{
			//if a sound has been loaded, toggle between playing and paused states
			soundManager.togglePause('nowplaying');
		}
	});

	//shuffle functionality!
	$('#shuffle').click(function()
	{
		if (shuffle)
		{
			shuffle = false;
			$('#shuffle').html('Shuffle is off');
		}
		else
		{
			shuffle = true;
			$('#shuffle').html('Shuffle is on');
		}
	});
});
