/**
 * A collection of handlebars.js helper functions that provide services to templates.
 * Assumes that jQuery and Handlebars have been included on the parent page
 */
$(function() {
	/**
	 * Outputs the length of the supplied array.
	 * TODO: remove this
	 *
	 * Usage:
	 * {{#arrayLength someArray}}
	 *		<p>The length of the array is {{length}}</p>
	 * {{else}}
	 		<p>The array is undefined or empty</p>
	 * {{/arrayLength}}
	 */
	Handlebars.registerHelper('arrayLength', function(array, options) {
		if (array && array.length) {
			console.log(array);
			var output = { length: array.length };
			console.log(JSON.stringify(output));
			return options.fn(output);
		} else {
			return options.inverse();
		}
	});

	/**
	 * Converts some number of seconds into a string of format MM:SS.
	 *
	 * Usage:
	 * {{#timeFormat seconds}}
	 */
	Handlebars.registerHelper('timeFormat', function(seconds, options) {
		var time = parseInt(seconds,10)
		var minutes = Math.floor(time / 60);
		var seconds = time % 60;

		//dumb hack to add leading zero to seconds
		if (seconds < 10) {
			return minutes + ":0" + seconds;
		} else {
			return minutes + ":" + seconds;
		}
	});

	/**
	 * Sub template for artists list elements
	 */
	Handlebars.registerPartial('artistListElement', $('#artist-list-element-template').html());

	/**
	 * Sub template for albums list elements
	 */
	Handlebars.registerPartial('albumListElementTemplate', $('#album-list-element-template').html());

	console.log('registered handlebars helpers');
});