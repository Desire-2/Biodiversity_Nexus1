# routes/gallery.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import GalleryItem
from app.forms import GalleryItemForm
from werkzeug.utils import secure_filename
import os

gallery = Blueprint('gallery', __name__)

@gallery.route('/gallery')
def gallery_view():
    gallery_items = GalleryItem.query.all()
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    if search_query:
        items = GalleryItem.query.filter(GalleryItem.title.like(f'%{search_query}%')).paginate(page=page, per_page=9)
    else:
        items = GalleryItem.query.paginate(page=page, per_page=9)
    return render_template('gallery.html', items=items, search_query=search_query, gallery_items=gallery_items)

@gallery.route('/admin/gallery', methods=['GET', 'POST'])
@login_required
def admin_gallery():
    if not current_user.role == "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))
    
    form = GalleryItemForm()
    if form.validate_on_submit():
        media_type = 'image' if form.file.data.mimetype.startswith('image/') else 'video'
        file_url = secure_filename(form.file.data.filename)
        form.file.data.save(os.path.join('static/uploads', file_url))

        item = GalleryItem(
            title=form.title.data,
            description=form.description.data,
            media_type=media_type,
            file_url=os.path.join('uploads', file_url),
            category=form.category.data,
            tags=form.tags.data,
            location=form.location.data,
            date_taken=form.date_taken.data
        )
        db.session.add(item)
        db.session.commit()
        flash('Gallery item added successfully!', 'success')
        return redirect(url_for('gallery.admin_gallery'))
    
    items = GalleryItem.query.all()
    return render_template('admin_gallery.html', form=form, items=items)

@gallery.route('/admin/gallery/delete/<int:id>', methods=['POST'])
@login_required
def delete_gallery_item(id):
    if not current_user.role == "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))

    item = GalleryItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Gallery item deleted successfully!', 'success')
    return redirect(url_for('gallery.admin_gallery'))

@gallery.route('/admin/gallery/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_gallery_item(id):
    if not current_user.role == "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))

    item = GalleryItem.query.get_or_404(id)
    form = GalleryItemForm()

    if form.validate_on_submit():
        item.title = form.title.data
        item.description = form.description.data
        if form.file.data:
            file_url = secure_filename(form.file.data.filename)
            form.file.data.save(os.path.join('static/uploads', file_url))
            item.file_url = os.path.join('uploads', file_url)
            item.media_type = 'image' if form.file.data.mimetype.startswith('image/') else 'video'
        item.category = form.category.data
        item.tags = form.tags.data
        item.location = form.location.data
        item.date_taken = form.date_taken.data

        db.session.commit()
        flash('Gallery item updated successfully!', 'success')
        return redirect(url_for('gallery.admin_gallery'))
    elif request.method == 'GET':
        form.title.data = item.title
        form.description.data = item.description
        form.category.data = item.category
        form.tags.data = item.tags
        form.location.data = item.location
        form.date_taken.data = item.date_taken

    return render_template('edit_gallery_item.html', form=form, item=item)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}

@gallery.route('/admin/gallery/manage', methods=['GET', 'POST'])
@login_required
def manage_gallery():
    if not current_user.role == "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join('static/uploads', filename))
            flash('File uploaded successfully!', 'success')
            return redirect(url_for('gallery.manage_gallery'))
        else:
            flash('Invalid file type', 'danger')
            return redirect(request.url)
    return render_template('admin/manage_gallery.html')