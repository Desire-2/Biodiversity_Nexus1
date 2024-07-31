from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db, app
from app.models import Project
from app.forms import ProjectForm
from flask_login import current_user, login_required
import os
import secrets
from PIL import Image


projects = Blueprint('projects', __name__)

def save_image(form_image):
    try:
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_image.filename)
        picture_fn = random_hex + f_ext
        picture_path = os.path.join(app.root_path, 'static/project_pics', picture_fn)

        output_size = (500, 500)
        i = Image.open(form_image)
        i.thumbnail(output_size)
        i.save(picture_path)

        return picture_fn
    except Exception as e:
        flash(f'An error occurred while saving the file: {e}', 'danger')
        return None

@projects.route('/projects')
def project_list():
    upcoming_projects = Project.query.filter_by(status='upcoming').all()
    completed_projects = Project.query.filter_by(status='completed').all()
    on_hold_projects = Project.query.filter_by(status='on hold').all()
    return render_template('projects.html', upcoming_projects=upcoming_projects, completed_projects=completed_projects, on_hold_projects=on_hold_projects)

@projects.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', title=project.title, project=project)


@projects.route('/project/new', methods=['GET', 'POST'])
@login_required
def new_project():
    if current_user.role != "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('projects.project_list'))
    
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(title=form.title.data,
                          description=form.description.data,
                          status=form.status.data,
                          progress=form.progress.data
                          )
        if form.image_url.data:
            image_file = save_image(form.image_url.data)
            project.image_url = image_file
        else:
            project.image_url = None
        db.session.add(project)
        db.session.commit()
        flash('Your project has been created!', 'success')
        return redirect(url_for('projects.project_list'))
    return render_template('create_project.html', title='New Project', form=form, legend='New Project')

@projects.route('/project/<int:project_id>/update', methods=['GET', 'POST'])
@login_required
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not current_user.role == "admin":
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('projects.project_list'))

    form = ProjectForm()
    if form.validate_on_submit():
        project.title = form.title.data
        project.description = form.description.data
        project.status = form.status.data
        project.progress = form.progress.data

        if form.image_url.data:
            image_file = save_image(form.image_url.data)
            project.image_url = image_file

        db.session.commit()
        flash('Your project has been updated!', 'success')
        return redirect(url_for('projects.project_list'))
    elif request.method == 'GET':
        form.title.data = project.title
        form.description.data = project.description
        form.status.data = project.status
        form.progress.data = project.progress
        form.image_url.data = project.image_url

    return render_template('create_project.html', title='Update Project', form=form, legend='Update Project')

@projects.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('projects.project_list'))

    db.session.delete(project)
    db.session.commit()
    flash('Your project has been deleted!', 'success')
    return redirect(url_for('projects.project_list'))

@projects.route('/projects/search', methods=['GET'])
def search_projects():
    query = request.args.get('query')
    status = request.args.get('status')
    projects = Project.query
    if query:
        projects = projects.filter(Project.title.contains(query) | Project.description.contains(query))
    if status:
        projects = projects.filter_by(status=status)
    projects = projects.all()
    return render_template('projects.html', projects=projects)

@projects.route('/projects/manage')
@login_required
def manage_projects():
    if current_user.role != 'admin':
        return redirect(url_for('main.index'))
    projects = Project.query.all()
    return render_template('manage_project.html', title='Manage Projects', projects=projects)
        