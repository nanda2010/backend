import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User

app, socketio = create_app()

with app.app_context():
    user = User.query.filter_by(email='jeevana@gmail.com').first()
    if user:
        print(f"👤 User: {user.email}")
        print(f"🔒 Status: {user.status}")
        print(f"🛠️ Role: {user.role}")
        
        if user.status != 'active':
            user.status = 'active'
            db.session.commit()
            print("🚀 STATUS OVERRIDE: Forced to 'active'.")
    else:
        print("❌ User not found.")
