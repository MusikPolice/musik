$(function() {
    //logical model of a user
    var User = Backbone.Model.extend({});

    //visual representation of a user
    var CurrentUserView = Backbone.View.extend({
        render: function() {
            this.el = ich.user(this.model.toJSON());
            return this;
        }
    })

    //drop the user into the DOM
    var currentUser = new User({username: "hello world"});
    var view = new CurrentUserView({model: currentUser});
    $('.content').append(view.render().el);
});