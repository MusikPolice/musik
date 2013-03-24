var ArtistsListView = Backbone.View.extend({
    el: $('.content'),

    initialize: function() {
        //remove the view on logout
        this.listenTo(dispatcher, 'logout', function() {
            $('.content div.artists').remove();
        });

        this._artistsList = new UpdatingCollectionView({
            collection: this.collection,
            childViewConstructor: ArtistListElementView,
            childViewTagName: 'li'
        });
    },

    render: function() {
        this.el = ich.artistsListView();
        $('.content').html(this.el);
        this._artistsList.el = $('.content ul.artists');
        this._artistsList.render();
    },
});