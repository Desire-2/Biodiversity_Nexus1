from flask import Blueprint, render_template, url_for, flash, redirect, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import Post, Thread, Comment
from app.forms import PostForm, ThreadForm, CommentForm

posts = Blueprint('posts', __name__)

@posts.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_post.html', title='New Post', form=form, legend='New Post')

@posts.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)

@posts.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user.role != 'admin':
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('posts.post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post', form=form, legend='Update Post')

@posts.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user.role != 'admin':
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('main.home'))

@posts.route("/admin/posts")
@login_required
def admin_posts():
    if current_user.role != 'admin':
        abort(403)
    posts = Post.query.all()
    return render_template('admin/admin_posts.html', posts=posts)

@posts.route("/admin/posts")
@login_required
def manage_posts():
    if current_user.role != 'admin':
        abort(403)
    posts = Post.query.all()
    return render_template('admin/admin_posts.html', posts=posts)
    
@posts.route("/thread/new", methods=['GET', 'POST'])
@login_required
def new_thread():
    form = ThreadForm()
    if form.validate_on_submit():
        thread = Thread(title=form.title.data, author_id=current_user.id)
        db.session.add(thread)
        db.session.commit()
        flash('Your thread has been created!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_thread.html', title='New Thread', form=form, legend='New Thread')

@posts.route("/thread/<int:thread_id>")
def thread(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    comments = Comment.query.filter_by(thread_id=thread.id).all()
    return render_template('thread.html', title=thread.title, thread=thread, comments=comments)

@posts.route("/thread/<int:thread_id>/comment", methods=['GET', 'POST'])
@login_required
def new_comment(thread_id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author_id=current_user.id, thread_id=thread_id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!', 'success')
        return redirect(url_for('posts.thread', thread_id=thread_id))
    return render_template('create_comment.html', title='New Comment', form=form, legend='New Comment')

@posts.route("/comment/<int:comment_id>/delete", methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.author != current_user:
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted!', 'success')
    return redirect(url_for('posts.thread', thread_id=comment.thread_id))
