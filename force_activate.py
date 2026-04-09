import sys
import os
# Add the backend directory to the path so we can import app and models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, PatientProfile, DoctorProfile
from flask_bcrypt import generate_password_hash

app, socketio = create_app()

with app.app_context():
    # 1. Activate ALL existing users
    users = User.query.all()
    for u in users:
        u.status = 'active'
    
    # 2. Ensure an Admin exists
    admin_email = "admin@perioguard.com"
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        hashed_pw = generate_password_hash("admin123").decode('utf-8')
        admin = User(
            name="System Administrator",
            email=admin_email,
            password=hashed_pw,
            role="admin",
            status="active"
        )
        db.session.add(admin)
        print(f"✨ Created Admin Account: {admin_email} / admin123")
    else:
        admin.status = "active"
        print("✅ Admin account activated.")

    db.session.commit()
    print(f"🚀 Successfully activated {len(users)} accounts. 'Straight Access' is now forced in the database.")
