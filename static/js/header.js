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

var player;

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