/*jslint browser: true*/
/*global $, jQuery*/

var pageTemplate = null;

/**
 * The currently playing sound object
 */
var nowplaying = null;

/**
 * True if shuffle play is on
 */
var shuffle = false;

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
 * Fetches the list of all artists from the server
 * The specified callback function will be called with the json object returned by the api on success
 */
 function getArtists(callback) {
    $.get('http://localhost:8080/api/artists')
    .done(function(data) {
        callback(data);
    })
    .fail(function() {
        console.log('GET request to /api/artists failed');
    });
}

/**
 * Fetches the artist with the specified id from the server
 * The specified callback function will be called with the json object returned by the api on success
 */
 function getArtist(id, callback) {
    $.get('http://localhost:8080/api/artists/id/' + id)
    .done(function(data) {
        callback(data);
    })
    .fail(function() {
        console.log('GET request to /api/artists/id/' + id + ' failed');
    });
}

/**
 * Fetches the album with the specified id from the server
 * The specified callback function will be called with the json object returned by the api on success
 */
 function getAlbum(id, callback) {
    $.get('http://localhost:8080/api/albums/id/' + id)
    .done(function(data) {
        callback(data);
    })
    .fail(function() {
        console.log('GET request to /api/albums/id/' + id + ' failed');
    });
}

/**
 * Sends the specified path to the server for importing.
 * The path must exist on the server and the service must have read permissions
 * at that path. The path can be a single file or a directory.
 */
function addMedia(p, callback) {
    console.log('sending import request for path ' + p);

    var json = {path: p};
    $.post('http://localhost:8080/api/importer', json)
    .done(function(data) {
        callback(data);
    })
    .fail(function() {
        console.log('POST request to /api/importer with path ' + p + ' failed');
    });
}

/**
 * Resets all jQuery event handlers after every page render
 */
 function hookEventHandlers() {
    'use strict';

    $('a').off('click.musik.nav');

    //nav toolbar links
    $('nav.navigation a.nowplaying').on('click.musik.nav', function(event) {
        'use strict'; 
        event.preventDefault();
        displayTemplate('#nowplaying-template', {});
    });
    $('nav.navigation a.artists').on('click.musik.nav', function(event) {
        'use strict'; 
        event.preventDefault();

        //fetch a list of artists from the api and display them in the template
        getArtists(function (data) {
            displayTemplate('#artists-template', data);
        });
    });
    $('nav.navigation a.albums').on('click.musik.nav', function(event) {
        'use strict'; 
        event.preventDefault();

        //fetch a list of albums from the api and display them in the template
        getAlbums(function (data) {
            displayTemplate('#albums-template', data);
        });
    });
    $('nav.navigation a.addmedia').on('click.musik.nav', function(event) {
        'use strict'; 
        event.preventDefault();
        displayTemplate('#addmedia-template', {});
    });

    //artist links
    $('a.artist-link').on('click.musik.nav', function(event) {
        'use strict';
        event.preventDefault();

        //fetch the full details for the appropriate artist
        var id = $(this).attr('artistId');
        getArtist(id, function(data) {
            //we only need the first artist in the returned list
            displayTemplate('#artist-details-template', data[0]);
        });
    });

    //album links
    $('.album-list-element a.album-link').on('click.musik.nav', function(event) {
        'use strict';
        event.preventDefault();

        //fetch the full details of the album
        var id = $(this).attr('albumId');
        getAlbum(id, function(data) {
            //we only needt he first result
            displayTemplate('#album-details-template', data[0]);
        });
    });

    //play track links
    $('.album-tracks tr.track td.controls a').off('click.track.play');
    $('.album-tracks tr.track td.controls a').on('click.track.play', function(event) {
        'use strict';
        event.preventDefault();

        var trackId = $(this).parents('tr.track').attr('trackId');
        var uri = '/api/stream/' + trackId;

        //TODO: load this uri into soundmanager2
        console.log("track stream url is " + uri);
        playSong(uri);
    });

    //play-pause control
    $('#playpause-control').on('click.track.play', function(event) {
        'use strict';
        event.preventDefault();

        if (nowplaying != null) {
            if (nowplaying.playState == 0) {
                nowplaying.play();
            } else if (nowplaying.playState == 1) {
                if (nowplaying.paused) {
                    nowplaying.resume();
                } else {
                    nowplaying.pause();
                }
            }
        }
    });

    //TODO browse for folder button
    //add media button
    $('form#importmedia button.addmedia').off('click.import.media');
    $('form#importmedia button.addmedia').on('click.import.media', function(event) {
        'use strict';
        event.preventDefault();
        console.log('add media button clicked');
        addMedia($('form#importmedia input#path').val())
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

/**
 * Initializes SoundManager2 so that we can play audio
 */
function initSoundManager2() {
    soundManager.setup({
        url: '/static/swf/',    //path to swf player in case html5 audio isn't supported
        preferFlash: false,     //ignore Flash where possible, use 100% HTML5 mode
        flashVersion: 9,        //if you must use flash, at least use flash 9
        onready: function() {
            //TODO: soundmanager is ready. do something about it
            console.log("SoundManager2 is ready for use.");
        },
        ontimeout: function(status) {
            //this will be hit if SM2 is falling back to flash but flash is not enabled
            //if the user then enables flash, onready will be hit
            console.log("Failed to load SoundManager2. Status is " + status.success + ", error type is " + status.error.type);
        }
    });
}

/*
* Plays the specified song url
*/
function playSong(url) {
    if (nowplaying != null) {
        nowplaying.stop();
        nowplaying.destruct();
    }

    //TODO: once multiple audio formats are supported, query SoundManager2 for the
    // browser's supported formats and dynamically request the appropriate one.

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

$(function() {
    'use strict';
    initSoundManager2();
    displayTemplate('#nowplaying-template', {});    
});