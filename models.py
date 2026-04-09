from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import json

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='patient') # 'patient', 'doctor', 'admin'
    status = db.Column(db.String(20), default='active') # 'active', 'pending_approval', 'suspended'
    profile_pic = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient_profile = db.relationship('PatientProfile', back_populates='patient_user', uselist=False, foreign_keys='PatientProfile.user_id')
    doctor_profile = db.relationship('DoctorProfile', back_populates='user', uselist=False, foreign_keys='DoctorProfile.user_id')
    notifications = db.relationship('Notification', backref='user', lazy=True)

class PatientProfile(db.Model):
    __tablename__ = 'patient_profiles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    patient_id = db.Column(db.String(50), unique=True, nullable=False, index=True) 
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    address = db.Column(db.String(255))
    medical_history = db.Column(db.Text)
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    patient_user = db.relationship('User', foreign_keys=[user_id], back_populates='patient_profile')
    assigned_doctor = db.relationship('User', foreign_keys=[assigned_doctor_id])

class DoctorProfile(db.Model):
    __tablename__ = 'doctor_profiles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    license_number = db.Column(db.String(100), unique=True)
    speciality = db.Column(db.String(100))
    experience_years = db.Column(db.Integer, default=0)
    hospital_name = db.Column(db.String(150))
    bio = db.Column(db.Text)
    availability = db.Column(db.JSON) # JSON of available slots/days
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], back_populates='doctor_profile')

class PatientAnalysis(db.Model):
    __tablename__ = 'patient_analysis'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    image_url = db.Column(db.String(255), nullable=False)
    predictions = db.Column(db.JSON) 
    bone_loss_mm = db.Column(db.Float)
    severity_label = db.Column(db.String(50))
    condition_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='PENDING') # PENDING, APPROVED, OVERRIDDEN
    doctor_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_user_id])
    doctor = db.relationship('User', foreign_keys=[doctor_user_id])

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default='PENDING') # PENDING, CONFIRMED, COMPLETED, CANCELLED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('User', foreign_keys=[patient_id])
    doctor = db.relationship('User', foreign_keys=[doctor_id])

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50)) # 'chat', 'appointment', 'diagnosis'
    read_status = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
