var musik;

$(function() {
    //event dispatcher
    var dispatcher = _.clone(Backbone.Events);

    //logical model of a user
    var User = Backbone.Model.extend({
        initialize: function() {
            this.username = null;
            this.token = null;
            this.expires = null;
        },

        login: function(username, password) {
            this.username = username;
            dispatcher.trigger('login');
        },

        logout: function() {
            this.username = null;
            dispatcher.trigger('logout');
        },

        toJSON: function() {
            return {'username': this.username,
                    'token': this.token,
                    'expires': this.expires};
        }
    });

    //visual representation of a user
    var CurrentUserView = Backbone.View.extend({
        el: $('nav'),

        initialize: function() {
            //show the view on login
            this.listenTo(dispatcher, 'login', function() {
                $('header').append(this.render().el);
            });

            //remove the view on logout
            this.listenTo(dispatcher, 'logout', function() {
                $('header .current-user').remove();
            });
        },

        events: {
            'click li a#logout': 'logout'
        },

        render: function() {
            this.el = ich.currentUser(this.model.toJSON());
            return this;
        },

        logout: function() {
            musik.currentUser.logout();
        }
    });

    //visual representation of the login form
    var LoginView = Backbone.View.extend({
        el: $('.content'),

        initialize: function() {
            this.listenTo(dispatcher, 'login', function() {
                $('input#password').val('');
            });
        },

        events: {
            'click button': 'submit'
        },

        render: function() {
            this.el = ich.login();
            return this;
        },

        submit: function() {
            musik.currentUser.login($('input#username').val(), $('input#password').val());
            return false;
        }
    });

    //make important objects visible to the debug console
    musik = {'currentUser': new User()}

    //create the current user view but don't display it yet
    var currentUserView = new CurrentUserView({model: musik.currentUser});

    //display the login view
    $('.content').html((new LoginView()).render().el);
});