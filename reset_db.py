
from app import create_app
from models import db
import os

app, socketio = create_app()

with app.app_context():
    print("--- Resetting database ---")
    # This will drop ALL tables
    db.drop_all()
    print("OK: All tables dropped.")
    # This will create ALL tables with the latest schema from models.py
    db.create_all()
    print("SUCCESS: All tables recreated successfully matches current models.")
