from app import app
from models import db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    existing_admin = User.query.filter_by(role='admin').first()

    if not existing_admin:
        hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')

        admin_user = User(
            username='admin',
            password=hashed_pw,
            role='admin'
        )

        db.session.add(admin_user)
        db.session.commit()
        print("Success: Admin user Created! (Username: admin, Password: admin123)")

    else:
        print("Admin user already exits in the database.")
