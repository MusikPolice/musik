App = Ember.Application.create({
    LOG_TRANSITIONS: true
});

App.IndexRoute = Ember.Route.extend({
  setupController: function(controller) {
    controller.set('nav-pages', ['Now Playing', 'Artists', 'Albums', 'Add Media', 'Search']);
    controller.set('player-controls', ['Play', 'Skip']);
    controller.set('user', {username: 'jfritz'});
  }
});