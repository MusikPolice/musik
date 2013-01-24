var musik;

$(function() {
    //event dispatcher
    var dispatcher = _.clone(Backbone.Events);

    //returns the contents of the HTTP Authorization header
    function getAuthHash() {
        var token = musik.currentUser.username + ':' + musik.currentUser.token;
        var hash = btoa(token);
        return 'Basic ' + hash;
    }

    //listen for ajax errors and throw a logout even when appropriate
    $(document).ajaxError(function(e, xhr, options) {
        if (xhr.status == 403) {
            console.log('firing logout event');
            musik.currentUser.logout();
        }
    });

    //logical model of a user
    var User = Backbone.Model.extend({
        initialize: function() {
            this.username = null;
            this.token = null;
            this.expires = null;
        },

        login: function(username, password) {
            $.ajax({
                type: 'PUT',
                url: '/api/currentuser',
                contentType: 'application/json; charset=utf-8',
                dataType: 'text',
                headers: {
                    'Authorization': getAuthHash()
                },
                success: function (data, textStatus, jqXHR) {
                    $.each(data, function(key, value) {
                        switch(key) {
                            case 'name':
                                this.username = value;
                                break;
                            case 'token':
                                this.token = value;
                                break;
                            case 'token_expires':
                                this.expires = value;
                                break;
                        }
                    });

                    //tell everybody else that the login succeeded
                    dispatcher.trigger('login');
                },
                error: function (data, textStatus, jqXHR) {
                    console.log('showing error message');
                    $('.login .error').show();
                }
            });
        },

        logout: function() {
            this.username = null;
            this.token = null;
            this.expires = null;
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
        el: $('header'),

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
            'click a#logout': 'logout'
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
            //hide login form once login is complete...
            this.listenTo(dispatcher, 'login', function() {
                $('.login').remove();
            });
            //...and show it again on logout
            this.listenTo(dispatcher, 'logout', function() {
                //only re-render the form if it isn't currently displayed
                if ($('.content div').attr('class') != 'login') {
                    this.render();
                }
            });
        },

        events: {
            'click button': 'submit'
        },

        render: function() {
            this.el = ich.login();
            $('.content').html(this.el);
            $('.login .error').hide();
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
    var loginView = new LoginView();
    loginView.render();
});