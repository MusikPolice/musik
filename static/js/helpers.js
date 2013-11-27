/**
 * A collection of handlebars.js helper functions that provide services to templates.
 * Assumes that jQuery and Handlebars have been included on the parent page
 */
$(function() {
	/**
	 * Outputs the length of the supplied array.
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

	console.log('registered handlebars helpers');
});