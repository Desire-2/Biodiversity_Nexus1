from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import db
from app.forms import VolunteerForm
from app.models import Volunteer, Project

volunteers = Blueprint('volunteers', __name__)

@volunteers.route('/volunteer/signup/<int:project_id>', methods=['GET', 'POST'])
def signup(project_id):
    project = Project.query.get_or_404(project_id)
    form = VolunteerForm()
    if form.validate_on_submit():
        volunteer = Volunteer(name=form.name.data, email=form.email.data, project_id=project.id)
        db.session.add(volunteer)
        db.session.commit()
        flash('Thank you for signing up as a volunteer!', 'success')
        return redirect(url_for('projects.project_detail', project_id=project.id))
    return render_template('volunteer_signup.html', title='Volunteer Signup', form=form, project=project)
