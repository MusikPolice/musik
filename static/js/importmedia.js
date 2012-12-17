$(document).ready(function() {
	$('.validate-error').hide();
});

$('#importmedia-form').submit(function(event) {

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
	$.ajax({
		type: 'POST',
		url: 'http://localhost:8080/api/importer/',
		contentType: 'application/json; charset=utf-8',
		data: $.toJSON(req),
		dataType: 'text',
		success: function(){
			alert('great success!');
		},
		error: function(jqXHR){
			alert(jqXHR.responseText);
		}
	});

	return true;
});
