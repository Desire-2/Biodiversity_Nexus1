from flask import Blueprint, render_template
from app.forms import SearchForm
from app.models import Event, Post

search = Blueprint('search', __name__)

@search.route('/search', methods=['GET', 'POST'])
def search_view():
    form = SearchForm()
    events = []
    posts = []
    if form.validate_on_submit():
        query = form.query.data
        events = Event.query.filter(Event.name.contains(query) | Event.description.contains(query)).all()
        posts = Post.query.filter(Post.title.contains(query) | Post.content.contains(query)).all()
    return render_template('search.html', form=form, events=events, posts=posts)
