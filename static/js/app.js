/*jslint browser: true*/
/*global $, jQuery*/

var pageTemplate = null;

/**
 * Details about the currently logged in user
 */
var user = {
    username: null,
    sessionToken: null,
    expiry: null
};

/**
 * The currently playing sound object
 */
var nowplaying = null;

/**
 * True if both the server and SM2 support audio/ogg vorbis
 */
var canPlayVorbis = false;

/**
 * True if both the server and SM2 support audio/mpeg mp3
 */
var canPlayMp3 = false;

/**
 * Fetches the list of mime types that the server is capable of encoding to
 */
function getEncoderMimeTypes(callback) {
    $.get('http://localhost:8080/api/stream/encoders')
    .done(function(data) {
        callback(JSON.parse(data));
    })
    .fail(function() {
        console.log('GET request to /api/stream/encoders failed');
    })
}

/**
 * Fetches the list of all albums from the server
 * The specified callback function will be called with json object returned by the api on success
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

    // is user logged in?
    $('header .current-user li').hide();
    if (user.sessionToken === null) {
        $('header .current-user li.logged-out').show();

        //TODO: force display of login template if user is not logged in

    } else {
        $('header .current-user li.logged-in a.username').html(user.username);
        $('header .current-user li.logged-in').show();
    }

    // login/register click handlers
    $('header .current-user a.login').on('click.musik.nav', function(event) {
        'use strict';
        event.preventDefault();
        displayTemplate('#login-template', {});
    });
    $('header .current-user a.logout').on('click.musik.nav', function(event) {
        'use strict';
        event.preventDefault();
        displayTemplate('#login-template', {});
    });
    $('#content .login a.register').on('click.musik.nav', function(event) {
        'use strict';
        event.preventDefault();
        displayTemplate('#register-template', {});
    });
    $('#content .register a.login').on('click.musik.nav', function(event) {
        'use strict';
        event.preventDefault();
        displayTemplate('#login-template', {});
    });

    //nav toolbar links

$('#content .login a.register').on('click.musik.nav', function(event) {
        'use strict';
        event.preventDefault();
        displayTemplate('#register-template', {});
    });    $('nav.navigation a.nowplaying').on('click.musik.nav', function(event) {
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
        var mimeType = $(this).attr('type')

        playSong(trackId, mimeType);
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
    //TODO: make pageTemplate a hash table keyed on templateSelector for efficiency++
    if (pageTemplate === null) {
        pageTemplate = Handlebars.compile($('#page-template').html());
    }

    //render the page wrapper - includes header, nav bar, login controls, etc
    $('#wrapper').html(pageTemplate({}));

    //build the requested template and dump it into the page contents block
    //TODO: long term, we could keep a global map of compiled templates
    var template = Handlebars.compile($(templateSelector).html());
    $('#content').html(template(params));

    hookEventHandlers();
}

/**
 * Initializes SoundManager2 so that we can play audio.
 * Along the way, this method finds the intersection of the types of audio that the server can
 * encode and the types of audio that SM2 can decode and sets the global canPlayMp3 and canPlayVorbis
 * fields so that we can select a compromise encoding when the native type of an audio file is not supported.
 *
 * mimeTypes: a list of mime type strings indicating the audio types that the server can encode to
 */
function initSoundManager2(mimeTypes) {
    soundManager.setup({
        url: '/static/swf/',    //path to swf player in case html5 audio isn't supported
        preferFlash: true,      //ignore Flash where possible, use 100% HTML5 mode
        flashVersion: 9,        //if you must use flash, at least use flash 9
        onready: function() {
            //SM2 is ready. check to see if browser supports each of the server's supported mime types
            // we only really care about ogg vorbis and mp3. everything else is impractical for streaming
            mimeTypes.forEach(function(mimeType) {
                if (mimeType === 'audio/mpeg' && soundManager.canPlayMIME(mimeType)) {
                    canPlayMp3 = true;
                }
                if (mimeType === 'audio/ogg' && soundManager.canPlayMIME(mimeType)) {
                    canPlayVorbis = true;
                }
            });
        },
        ontimeout: function(status) {
            //this will be hit if SM2 is falling back to flash but flash is not enabled
            //if the user then enables flash, onready will be hit
            console.log("Failed to load SoundManager2. Status is " + status.success + ", error type is " + status.error.type);
        }
    });
}

/**
 * Stops the currently playing song, destructs the song object, and sets it to null
 */
function stopSong() {
    if (nowplaying != null) {
        nowplaying.stop();
        nowplaying.destruct();
        nowplaying = null;
    }
}

/*
* Plays the specified song
* trackId: the unique identifier of the track to play
* mimeType: the mime type of the track if known, else null
* returns false on error
*/
function playSong(trackId, mimeType) {
    //make sure we're initialized
    if (!soundManager.ok()) {
        return false;
    }

    //stop currently playing song if necessary
    stopSong();

    console.log('Native mime type of file is ' + mimeType);
    if (mimeType === null || soundManager.canPlayMIME(mimeType) === false) {
        // we either don't know the mime type of the file or we can't play it, try to get it transcoded
        if (canPlayVorbis) {
            mimeType = 'audio/ogg';
        } else if (canPlayMp3) {
            mimeType = 'audio/mpeg';
        } else {
            console.error('Native mime type of file is not supported and no compromise format could be selected.');
            return false;
        }
        console.log('Native mime type of file is not supported. Requesting ' + mimeType + ' instead.');
    }

    //assemble the uri of the track
    var uri = '/api/stream/' + trackId + '/' + mimeType.split('/')[1];
    console.log('Loading ' + uri);

    //play the requested song
    nowplaying = soundManager.createSound({
        autoLoad: true,
        autoPlay: true,
        id: 'nowplaying',
        type: mimeType,
        url: uri,
        onfinish: function() {
            //destroy the sound
            $('#playpause-control').html('Play');
            stopSong();
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

    //fetch the mime types that the server can encode to 
    //and pass them to the sound manager initialization
    getEncoderMimeTypes(initSoundManager2);

    //show the home page
    displayTemplate('#nowplaying-template', {});    
});