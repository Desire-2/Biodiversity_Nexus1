from flask import Blueprint

from app.routes.main import main
from app.routes.auth import auth
from app.routes.events import events
from app.routes.admin import admin
from app.routes.search import search
from app.routes.messages import messages
from app.routes.donations import donations
from app.routes.projects import projects
from app.routes.volunteers import volunteers
from app.routes.gallery import gallery
from app.routes.posts import posts

blueprints = [
    main,
    auth,
    events,
    admin,
    search,
    messages,
    donations,
    projects,
    volunteers,
    gallery,
    posts
    ]

def register_blueprints(app):
    for bp in blueprints:
        app.register_blueprint(bp)
