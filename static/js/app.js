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
    this.route('albums');
    this.route('addmedia');
});

//an artist object that can fetch artists from the server
App.Artist = Ember.Object.extend({});
App.Artist.reopenClass({
  allArtists: [],
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
  }
});

//links artist object to the /artist route
App.ArtistsRoute = Ember.Route.extend({
  model: function() {
    return App.Artist.all();
  }
});