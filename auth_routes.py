from flask import Blueprint, request, jsonify
from models import db, User, PatientProfile, DoctorProfile, AuditLog, bcrypt
from middleware import token_required
import jwt
from datetime import datetime, timedelta
import os

auth_bp = Blueprint('auth', __name__)
SECRET_KEY = os.environ.get('SECRET_KEY', 'perioguard-secret-key-high-end-2026')

def generate_token(user_id, role, name):
    payload = {
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
        'sub': user_id,
        'role': role,
        'name': name
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    role = data.get('role', 'patient')
    if role not in ['doctor', 'patient']:
        role = 'patient' # Force non-admin role
    phone = data.get('phone')

    if not all([email, password, name]):
        return jsonify({"error": "Missing email, password, or name"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # Straight Access: No admin approval required as requested
    status = 'active'
    
    new_user = User(
        name=name, 
        email=email, 
        password=hashed_password, 
        role=role, 
        phone=phone,
        status=status
    )
    db.session.add(new_user)
    db.session.flush() # Get ID before commit

    if role == 'patient':
        # Create a patient profile with a generated clinical ID
        patient_id = f"PAT-{new_user.id:03d}"
        profile = PatientProfile(
            user_id=new_user.id, 
            patient_id=patient_id,
            assigned_doctor_id=data.get('assigned_doctor_id')
        )
        db.session.add(profile)
    elif role == 'doctor':
        # Create doctor profile
        profile = DoctorProfile(
            user_id=new_user.id,
            license_number=data.get('license_number'),
            speciality=data.get('speciality'),
            hospital_name=data.get('hospital_name')
        )
        db.session.add(profile)

    db.session.commit()
    
    return jsonify({
        "message": f"{role.capitalize()} registered successfully",
        "status": status,
        "user_id": new_user.id
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('email') or data.get('patient_id')
    password = data.get('password')
    required_role = data.get('role') # Role from the frontend (doctor vs patient)

    if not identifier or not password:
        return jsonify({"error": "Credentials required"}), 400

    # Find user
    user = User.query.filter_by(email=identifier).first()
    if not user:
        p_profile = PatientProfile.query.filter_by(patient_id=identifier).first()
        if p_profile: user = User.query.get(p_profile.user_id)

    if user and bcrypt.check_password_hash(user.password, password):
        # Role Isolation Check
        if required_role and user.role != required_role:
            return jsonify({"error": f"Role mismatch. Use the {user.role.capitalize()} Portal."}), 403

        # Removed status block for Straight Access
        # if user.status == 'pending_approval' or user.status == 'suspended': ...

        token = generate_token(user.id, user.role, user.name)
        
        # Log entry
        log = AuditLog(user_id=user.id, action='LOGIN', details=f"Logged in as {user.role}")
        db.session.add(log)
        db.session.commit()

        return jsonify({
            "token": token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "patient_id": user.patient_profile.patient_id if user.role == 'patient' else None
            }
        }), 200

    return jsonify({"error": "Invalid credentials"}), 401

@auth_bp.route('/check', methods=['GET'])
def check_status():
    return jsonify({"status": "online", "service": "PerioGuard AI"}), 200

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "patient_id": current_user.patient_profile.patient_id if current_user.role == 'patient' else None
    }), 200

