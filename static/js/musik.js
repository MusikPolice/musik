var musik;

$(function() {
    //logical model of a user
    var User = Backbone.Model.extend({
        login: function(username, password) {
            alert('Login Called with username ' + username + ' password ' + password);
            return true;
        }
    });

    //visual representation of a user
    var CurrentUserView = Backbone.View.extend({
        render: function() {
            this.el = ich.currentUser(this.model.toJSON());
            return this;
        }
    });

    //visual representation of the login form
    var LoginView = Backbone.View.extend({
        el: $('.content'),

        events: {
            'click button': 'balls'
        },

        render: function() {
            this.el = ich.login();
            return this;
        },

        balls: function() {
            currentUser.login($('input#username').val(), $('input#password').val());
            return false;
        }
    });

    //drop the user into the DOM
    var currentUser = new User({username: "hello world"});
    $('header').append((new CurrentUserView({model: currentUser})).render().el);
    $('.content').html((new LoginView()).render().el);

    //make important objects visible to the debug console
    musik = {'currentUser': currentUser}
});