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

    //listen for ajax errors and throw a logout when appropriate
    $(document).ajaxError(function(e, xhr, options) {
        if (xhr.status == 403) {
            console.log('firing logout event');
            musik.currentUser.logout();
        }
    });

    //logical model of a user
    var User = Backbone.Model.extend({

        //attempts to log in with specified username and password
        //on success, login event is thrown
        login: function(username, password) {
            var self = this;
            console.log('attempting to log in user with username=' + username + ', password=' + password);

            self.id = 0;
            Backbone.BasicAuth.set(username, password);
            this.save({'username': username, 'token': password}, {
                url: 'api/currentuser',
                success: function(model, response, options) {
                    console.log('save success handler fired.');
                    console.log(model.get('id'));
                    console.log(model.get('username'));
                    console.log(model.get('token'));
                    Backbone.BasicAuth.set(model.get('username'), model.get('token'));
                    dispatcher.trigger('login');
                },
                error: function(model, xhr, options) {
                    console.log('login error.');
                    self.clear();
                    Backbone.BasicAuth.clear();
                    musik.loginView.showError();
                }
            });
        },

        //attempts to register a new user account with specified username and password
        //on success, the new user will be automatically logged in
        register: function(username, password) {
            var self = this;
            console.log('attempting to register user with username=' + username + ', password=' + password);

            //create the new account
            this.save({'username': username, 'token': password}, {
                url: '/api/users',
                success: function (model, response, options) {
                    console.log('successfully registered ' + username);
                    console.log('id ' + model.get('id'));
                    console.log('created ' + model.get('created'));
                    self.login(username, password);
                },
                error: function (model, xhr, options) {
                    console.log('failed to register ' + username)
                    self.clear();
                    musik.registerView.showError('Ah shit you broke it. Try again later.');
                }
            });
        },

        logout: function() {
            console.log('logging out');
            this.clear();
            dispatcher.trigger('logout');
        },

        clear: function() {
            this.set({id: null, username: null, token: null, token_expires: null, created: null});
            Backbone.BasicAuth.clear();
        }
    });

    //a collection of user accounts
    var UserAccounts = Backbone.Collection.extend({
        model: User,
        url: '/api/users'
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

    //the navigation menu
    var NavigationView = Backbone.View.extend({
        el: $('header'),

        initialize: function() {
            //show the view on login
            this.listenTo(dispatcher, 'login', function() {
                console.log('showing navigation view');
                this.render();
            });

            //remove the view on logout
            this.listenTo(dispatcher, 'logout', function() {
                console.log('hiding navigation view');
                $('header nav.navigation').remove();
            });
        },

        events: {
            'click .pages a.nowplaying-nav': 'showNowPlaying',
            'click .pages a.artists-nav': 'showArtists',
            'click .pages a.albums-nav': 'showAlbums',
            'click .pages a.addmedia-nav': 'showAddMedia'
        },

        render: function() {
            this.el = ich.navigation();
            $('header').append(this.el);
            return this;
        },

        showNowPlaying: function() {
            musik.nowPlayingView.render();
        },

        showArtists: function() {
            musik.artistsView.render();
        },

        showAlbums: function() {
            alert('albums');
        },

        showAddMedia: function() {
            musik.addMediaView.render();
        }
    });

    //visual representation of the login form
    var LoginView = Backbone.View.extend({
        el: $('.content'),

        initialize: function() {
            //hide login form once login is complete...
            this.listenTo(dispatcher, 'login', function() {
                $('div.login').remove();
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
            'click button.login': 'submit',
            'click a.register': 'register'
        },

        render: function() {
            console.log('showing login view');
            this.el = ich.login();
            $('.content').html(this.el);
            $('.login .error').hide();
            $('.login input#username').focus();
            return this;
        },

        showError: function() {
            console.log('showing error message');
            $('.login input').val('');
            $('.login input#username').focus();
            $('.login .error').slideDown(400);
        },

        submit: function() {
            console.log('log in submit button pressed');
            musik.currentUser.login($('input#username').val(), $('input#password').val());
            return false;
        },

        register: function() {
            musik.registerView.render();
        }
    });

    //registration form view
    var RegisterView = Backbone.View.extend({
        el: $('.content'),

        initialize: function() {
            //hide form on logout
            this.listenTo(dispatcher, 'logout', function() {
                $('div.register').remove();
            });
        },

        events: {
            'click button.register': 'submit',
            'click a.login': 'login'
        },

        render: function() {
            console.log('showing register view');
            this.el = ich.register();
            $('.content').html(this.el);
            $('.register input#username').focus();
            return this;
        },

        showError: function(msg) {
            console.log('showing error message');
            $('.register input#password, .register input#password2').val('');
            $('.register .error p').html(msg);
            $('.register .error').slideDown(400);
        },

        submit: function() {
            console.log('register submit button pressed');

            var accounts = new UserAccounts();
            accounts.fetch({
                success: function(model, response, options) {
                    console.log('Found ' + accounts.models.length + ' existing user accounts.');

                    //make sure that the chosen username is unique
                    var unique = true;
                    _.each(accounts.models, function(element, index, list) { 
                        if (element.get('username') == $('.register input#username').val()) {
                            unique = false;
                            return;
                        }
                    });
                    if (!unique) {
                        console.log('Chosen username is not unique.');
                        musik.registerView.showError('Pick a unique username, fool.');
                        $('.register input#username').focus();
                        return false;
                    }

                    //make sure that passwords have length
                    if ($('input#password').val().length == 0 || $('input#password2').val().length == 0) {
                        console.log('Empty password not allowed.');
                        musik.registerView.showError('Dude, you gotta enter a password.');
                        $('.register input#password').focus();
                        return false;
                    }

                    //make sure that the passwords match
                    if ($('input#password').val() != $('input#password2').val()) {
                        console.log('Chosen passwords do not match.');
                        musik.registerView.showError('Those passwords don\'t match, homie.');
                        $('.register input#password').focus();
                        return false;
                    }

                    //actually create the account
                    musik.currentUser.register($('input#username').val(), $('input#password').val());
                },
                error: function(model, xhr, options) {
                    console.log('failed to fetch existing user accounts.');
                    musik.registerView.showError('Hmm, something is broken. Come back later.');
                }
            });

            return false;
        },

        login: function() {
            console.log('login link clicked');
            musik.loginView.render();
        }
    });

    var NowPlayingView = Backbone.View.extend({
        el: $('.content'),

        initialize: function() {
            //show the view on login
            this.listenTo(dispatcher, 'login', function() {
                this.render();
            });

            //remove the view on logout
            this.listenTo(dispatcher, 'logout', function() {
                $('.content div.nowplaying').remove();
            });
        },

        render: function() {
            this.el = ich.nowplaying();
            $('.content').html(this.el);
            return this;
        },
    });

    var ArtistsView = Backbone.View.extend({
        el: $('.content'),

        initialize: function() {
            //remove the view on logout
            this.listenTo(dispatcher, 'logout', function() {
                $('.content div.artists').remove();
            });
        },

        render: function() {
            this.el = ich.artists();
            $('.content').html(this.el);
            return this;
        },
    });

    //import media page
    var AddMediaView = Backbone.View.extend({
        el: $('.content'),

        initialize: function() {
            //remove the view on logout
            this.listenTo(dispatcher, 'logout', function() {
                $('.content div.addmedia').remove();
            });
        },

        events: {
            'click input.browse': 'browse',
            'click button.addmedia': 'submit'
        },

        render: function() {
            this.el = ich.addmedia();
            $('.content').html(this.el);
            $('.addmedia .error').hide();
            $('.addmedia .success').hide();
            $('.addmedia #importmedia #path').focus();
            return this;
        },

        browse: function() {
            console.log('Add media browse button clicked.');
            return false;
        },

        submit: function() {
            console.log('Add media submit button clicked.');
            $('.addmedia .error').hide();
            $('.addmedia .success').hide();

            //TODO: better error handling here wouldn't be so bad
            var p = $('.addmedia #importmedia #path').val();
            if (p == '') {
                musik.addMediaView.showError('That\'s not a real path. Try again, skipper.');
                return false;
            }

            $.ajax({
                type: 'POST',
                url: '/api/importer/',
                contentType: 'application/json; charset=utf-8',
                data: JSON.stringify({
                    path: p
                }),
                headers: {
                    'Authorization': getAuthHash()
                },
                dataType: 'text',
                success: function() {
                    musik.addMediaView.showSuccess('Great success!<br />Your media is being imported.');
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    if (jqXHR.status == 404) {
                        musik.addMediaView.showError('That path doesn\'t exist.');
                    } else {
                        musik.addMediaView.showError('Something broke. Try again later.');
                    }
                }
            });

            return false;
        },

        showError: function(msg) {
            console.log('showing error message');
            $('.addmedia .success').hide();
            $('.addmedia #importmedia #path').val('');
            $('.addmedia .error p').html(msg);
            $('.addmedia .error').slideDown(400);
            $('.addmedia #importmedia #path').focus();
        },

        showSuccess: function(msg) {
            console.log('showing success message');
            $('.addmedia .error').hide();
            $('.addmedia #importmedia #path').val('');
            $('.addmedia .success p').html(msg);
            $('.addmedia .success').slideDown(400);
            $('.addmedia #importmedia #path').focus();
        }
    });

    //make important objects visible to the debug console
    musik = {}
    musik['currentUser'] = new User();
    musik['loginView'] = new LoginView()
    musik['registerView'] = new RegisterView()
    musik['currentUserView'] = new CurrentUserView({model: musik.currentUser})
    musik['navigationView'] = new NavigationView();
    musik['nowPlayingView'] = new NowPlayingView();
    musik['artistsView'] = new ArtistsView();
    musik['addMediaView'] = new AddMediaView();

    //display the login view
    musik.loginView.render();
});