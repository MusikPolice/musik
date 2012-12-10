/*
 * An HTML5 audio player
 */
var player;

/*
 * Create an HTML5 audio player on load and hook up some basic controls
 */
$(document).ready(function() {
	//create the player
	player = document.createElement('audio');
	player.setAttribute('src', 'http://localhost:8080/api/stream/track/1');

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
	})
})

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