from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, Event, GalleryItem, ActivityLog
from app import db
from app.forms import EditUserForm

admin = Blueprint('admin', __name__)


@admin.route('/admin/dashboard')
@login_required
def dashboard():
    if not current_user.role == "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))

    total_events = Event.query.count()
    total_gallery_items = GalleryItem.query.count()
    total_users = User.query.count()
    recent_activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                           total_events=total_events,
                           total_gallery_items=total_gallery_items,
                           total_users=total_users,
                           recent_activities=recent_activities)


@admin.route('/admin/manage_events')
@login_required
def manage_events():
    if current_user.role != 'admin':
        return redirect(url_for('main.index'))
    events = Event.query.all()
    return render_template('manage_events.html', events=events)

@admin.route('/admin/manage_donations')
@login_required
def manage_donations():
    if current_user.role != 'admin':
        return redirect(url_for('main.index'))
    donations = Donation.query.all()
    return render_template('manage_donations.html', donations=donations)

@admin.route('/admin/manage_users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        return redirect(url_for('main.index'))
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@admin.route('/admin/edit_user/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if current_user.role != 'admin':
        return redirect(url_for('main.index'))
    user = User.query.get_or_404(id)
    form = EditUserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('edit_user.html', form=form, user=user)

@admin.route('/admin/delete_user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.role != 'admin':
        return redirect(url_for('main.index'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.manage_users'))
