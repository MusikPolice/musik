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