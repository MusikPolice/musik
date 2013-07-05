//create the application
App = Ember.Application.create({
    LOG_TRANSITIONS: true
});

/**
 * Artists
 */
App.Artist = Ember.Object.extend({});
App.Artist.reopenClass({
  
  all: function() {
    var allArtists = [];
    $.ajax({
      url: '/api/artists',
      dataType: 'json',
      context: this,
      success: function(response) {
        $.each(response, function(i, item) {
          allArtists.addObject(App.Artist.create(response[i]));
        })
      }
    });
    return allArtists;
  },

  find: function(artist_id) {
    var artist = App.Artist.create();
    $.ajax({
      url: '/api/artists/id/' + artist_id,
      dataType: 'json',
      context: this,
      success: function(response) {
        $.each(response, function(i, item) {
          artist.setProperties(response[i]);
        })
      }
    });
    artist.set('id', artist_id);
    return artist;
  }
});

//links artist object to the /artists route
App.ArtistsRoute = Ember.Route.extend({
  model: function() {
    return App.Artist.all();
  }
});

//links artist object to the /artist route
App.ArtistRoute = Ember.Route.extend({
  model: function(params) {
    return App.Artist.find(params.artist_id);
  }
});

/**
 * Albums
 */
App.Album = Ember.Object.extend({});
App.Album.reopenClass({

  all: function() {
    var allAlbums = [];
    $.ajax({
      url: '/api/albums',
      dataType: 'json',
      context: this,
      success: function(response) {
        $.each(response, function(i, item) {
          allAlbums.addObject(App.Album.create(response[i]));
        })
      }
    });
    return allAlbums;
  },

  find: function(album_id) {
    var album = App.Album.create();
    $.ajax({
      url: '/api/albums/id/' + album_id,
      dataType: 'json',
      context: this,
      success: function(response) {
        $.each(response, function(i, item) {
          album.setProperties(response[i]);
        })
      }
    });
    album.set('id', album_id);
    return album;
  }
});

//links album object to the /albums route
App.AlbumsRoute = Ember.Route.extend({
  model: function() {
    return App.Album.all();
  }
});

//links album object to the /album route
App.AlbumRoute = Ember.Route.extend({
  model: function(params) {
    return App.Album.find(params.album_id);
  }
});

/**
 * Users
 */
App.User = Ember.Object.extend({});
App.User.reopenClass({

  all: function() {
    var allUsers = [];
    $.ajax({
      url: '/api/users',
      dataType: 'json',
      context: this,
      success: function(response) {
        $.each(response, function(i, item) {
          allUsers.addObject(App.User.create(response[i]));
        })
      }
    });
    return allUsers;
  }
});

/**
 * Add Media
 */
App.AddmediaController = Ember.ObjectController.extend({
  browse: function() {
    alert("TODO: pop a browse dialog");
  },
  submit: function() {
    var importpath = $('input#path').val();
    $.ajax({
      url: '/api/importer',
      contentType: 'application/json',
      data: '{"path": "' + importpath + '"}',
      dataType: 'application/json',
      type: 'POST',
      context: this,
      success: function(response) {
        //TODO: eventually, this should start looking for importer messages
        //      to show the user the status of the importer in browser.
        alert('Import path' + importpath +' successfully submitted.');
      },
      error: function(response) {
        alert('Failed to submit path for import.');
      }
    });
  }
});

/**
 * Application entry point
 */
//allows for pretty urls and back/forward button use
App.Router.reopen({
    location: 'history'
});

//sets up the main application controller
App.ApplicationController = Ember.Controller.extend({
    user: App.User.create()
});

//maps urls for application pages
App.Router.map(function() {
    this.route('register');
    this.route('login');
    this.route('nowplaying')
    this.route('artists');
    this.route('artist', {path: '/artist/:artist_id'});
    this.route('albums');
    this.route('album', {path: '/album/:album_id'});
    this.route('addmedia');
});