from app import app, db

# Create the application context
with app.app_context():
    # Now you can perform operations that require the application context
    db.create_all()