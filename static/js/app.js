//creates the application
App = Ember.Application.create({
    LOG_TRANSITIONS: true
});

//allows for pretty urls and back/forward button use
App.Router.reopen({
    location: 'history'
});

//sets up the main application controller
App.ApplicationController = Ember.Controller.extend({
    user: null
});

//maps urls for application pages
App.Router.map(function() {
    this.route('register');
    this.route('login');
    this.route('nowplaying')
    this.route('artists');
    this.route('artist', {path: '/artist/:artist_id'});
    this.route('albums');
    this.route('addmedia');
});

//an artist object that can fetch artists from the server
App.Artist = Ember.Object.extend({});
App.Artist.reopenClass({
  allArtists: [],
  artist: null,

  all: function() {
    var self = this;
    this.allArtists = [];
    $.ajax({
      url: '/api/artists',
      dataType: 'json',
      context: this,
      success: function(response) {
        $.each(response, function(i, item) {
          self.allArtists.addObject(App.Artist.create(response[i]));
        })
      }
    });
    return this.allArtists;
  },

  find: function(artist_id) {
    var self = this;
    this.artist = App.Artist.create();
    $.ajax({
      url: '/api/artists/id/' + artist_id,
      dataType: 'json',
      context: this,
      success: function(response) {
        $.each(response, function(i, item) {
          self.artist.setProperties(response[i]);
        })
      }
    });
    this.artist.set('id', artist_id);
    return this.artist;
  }
});

//links artist object to the /artist route
App.ArtistsRoute = Ember.Route.extend({
  model: function() {
    return App.Artist.all();
  }
});

App.ArtistRoute = Ember.Route.extend({
  model: function(params) {
    return App.Artist.find(params.artist_id);
  }
});