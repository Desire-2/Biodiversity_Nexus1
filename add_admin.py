from app import app, db, bcrypt
from app.models import User


with app.app_context():
    # Check if the user already exists
    user = User.query.filter_by(email='bikorimanadesire@yahoo.com').first()
    if user is None:
        # Create a new admin user
        hashed_password = bcrypt.generate_password_hash('Desire@#1').decode('utf-8')
        new_admin = User(username='Desire', email='bikorimanadesire@yahoo.com', password=hashed_password, role='admin')
        db.session.add(new_admin)
        db.session.commit()
        print('Admin user created successfully!')
    else:
        print('Admin user already exists.')
