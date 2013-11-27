/*jslint browser: true*/
/*global $, jQuery*/

var pageTemplate = null;

/**
 * Fetches the list of all albums from the server
 * The specified callback function will be called with json object returned by the api on success
 * 
 */
function getAlbums(callback) {
    $.get('http://localhost:8080/api/albums')
        .done(function(data) {
            callback(data);
        })
        .fail(function() {
            console.log('GET request to /api/albums failed');
        });
}

/**
 * Resets all jQuery event handlers after every page render
 */
function hookEventHandlers() {
    'use strict';

    //nav links
    $('nav.navigation a').off('click.musik.nav');
    $('nav.navigation a.nowplaying').on('click.musik.nav', function(event) {
        'use strict'; 
        event.preventDefault();
        displayTemplate('#nowplaying-template', {});
    });
    $('nav.navigation a.artists').on('click.musik.nav', function(event) {
        'use strict'; 
        event.preventDefault();
        displayTemplate('#artists-template', {});
    });
    $('nav.navigation a.albums').on('click.musik.nav', function(event) {
        'use strict'; 
        event.preventDefault();

        //fetch a list of albums from the api and display them in the template
        getAlbums(function (data) {
            console.log('getAlbums callback');
            displayTemplate('#albums-template', data);
        });
    });
    $('nav.navigation a.addmedia').on('click.musik.nav', function(event) {
        'use strict'; 
        event.preventDefault();
        displayTemplate('#addmedia-template', {});
    });

    console.log('reset event handlers');
}

/**
 * Re-draws the page, putting the specified template into the #content div
 * The specified params map will be passed to the template at display time 
 *
 * templateSelector: String - a jQuery selector for the template to be placed into the #content div of the page
 * params: Object - a map of values to be passed into the template at display time
 */
function displayTemplate(templateSelector, params) {
    'use strict';

    console.log('Displaying ' + templateSelector);

    //only keep one compiled copy of the page template on hand
    if (pageTemplate === null) {
        pageTemplate = Handlebars.compile($('#page-template').html());
    }

    //TODO: any template info that the header needs must be fetched here
    $('#wrapper').html(pageTemplate({}));

    //build the requested template and dump it into the page contents block
    //TODO: long term, we could keep a global map of compiled templates
    var template = Handlebars.compile($(templateSelector).html());
    $('#content').html(template(params));

    hookEventHandlers();
}

$(function() {
    'use strict';
    displayTemplate('#nowplaying-template', {});    
});