from app import create_app
from models import db, User

app, socketio = create_app()

with app.app_context():
    # Find all doctors and set them to active immediately for dev mode
    doctors = User.query.filter_by(role='doctor').all()
    for d in doctors:
        d.status = 'active'
    db.session.commit()
    print(f"✅ Successfully approved {len(doctors)} doctor accounts. Access Granted.")
