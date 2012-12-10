/*
 * An HTML5 audio player
 */
var player;

/*
 * True if shuffle is on
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
 * Loads the specified uri into the streaming player and starts it playing
 */
function play_uri(uri)
{
	player.setAttribute('src', uri);
	if (player.paused)
	{
		player.play();
		$('#playpause').html('Pause');
	}
}

/**
 * Loads a random track from the library into the player
 */
function load_random_track()
{
	if (shuffle)
	{
		//load a random track
		$.get('/api/tracks/random', function(data)
		{
			alert(data['stream_uri']);
			play_uri(data['stream_uri']);
		});
	}
	else
	{
		//update controls state
		$('#playpause').html('Play');
	}
}

/*
 * Create an HTML5 audio player on load and hook up some basic controls
 */
$(document).ready(function() {
	//create the player
	player = document.createElement('audio');

	//load a random track but don't start playing yet
	$.get('/api/tracks/random', function(data)
	{
		player.setAttribute('src', data['stream_uri']);
		if (!player.paused)
		{
			player.pause();
		}
	});

	//hook up controls
	$('#playpause').click(function() {
		if (player.paused)
		{
			player.play();
			$('#playpause').html('Pause');
		}
		else
		{
			player.pause();
			$('#playpause').html('Play');
		}
	});

	//on track end, if shuffle mode is active, we want to load the next track
	player.addEventListener('ended', load_random_track(), false);
})