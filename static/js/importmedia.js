var nullCount = 0

function update_status() {
	$.ajax({
		type: 'GET',
		url: 'http://localhost:8080/api/importer/',
		contentType: 'application/json; charset=utf-8',
		success: function(data, textStatus, jqXHR) {
			if (data['current_task'] != null) {
				//update the status display
				$('#status .numtasks').html(data['outstanding_tasks']);
				$('#status .currenttask').html(data['current_task']['uri']);
			}
			else
			{
				$('#status .numtasks').html('0');
				$('#status .currenttask').html('None');
			}

			if (data['warnings'] != null && data['warnings'].length > 0) {
				$('#warnings ul').html('');
				for (var i = 0; i < data['warnings'].length; i++) {
					$('#warnings ul').append('<li>' + data['warnings'][i]['message'] + '</li>');
				}
				$('#warnings').show();
			}

			if (data['errors'] != null && data['errors'].length > 0) {
				$('#errors ul').html('');
				for (var i = 0; i < data['errors'].length; i++) {
					$('#errors ul').append('<li>' + data['errors'][i]['message'] + '</li>');
				}
				$('#errors').show();
			}

			if (data['outstanding_tasks'] == 0) {
				nullCount += 1;
			}
			else
			{
				nullCount = 0;
			}

			//we'll fire 10 extra requests after the number of outstanding tasks first appears to be zero.
			//this should help to account for the importer taking a moment to respond to our requests
			if (nullCount < 10) {
				//do it again in a half second
				setTimeout(update_status, 500);
			}
		},
		dataType: 'json'
	});
}

$(document).ready(function() {
	$('.validate-error').hide();
	$('#warnings').hide();
	$('#errors').hide();
	update_status();
});

$('#importmedia').submit(function(event) {

	//stop the form from submitting normally
	event.preventDefault();

	$('.validate-error').html('');
	$('.validate-error').hide();

	// TODO: better path validation is a plus
	if ($('#path').val() == '') {
		$('#validate-error-top').html("Please provide a valid path to continue.");
		$('.validate-error').show();
		$('#path').focus();
		return false;
	}

	var req = {
		path: $('#path').val()
	}
	//TODO: error and success handling need some work
	nullCount = 0;
	$.ajax({
		type: 'POST',
		url: 'http://localhost:8080/api/importer/',
		contentType: 'application/json; charset=utf-8',
		data: $.toJSON(req),
		dataType: 'text',
		success: update_status(),
		error: function(jqXHR){
			alert(jqXHR.responseText);
		}
	});

	return true;
});
