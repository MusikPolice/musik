var ArtistListElementView = Backbone.View.extend({
    initialize: function() {
        this.render = _.bind(this.render, this);
        this.model.bind('change', this.render);
    },

    render: function() {
        $(this.el).empty();
        ich.artistListElementView(this.model).appendTo(this.el);
    }
});