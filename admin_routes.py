from flask import Blueprint, request, jsonify
from models import db, User, DoctorProfile, PatientProfile, PatientAnalysis
from middleware import token_required, roles_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
@token_required
@roles_required('admin')
def get_all_users(current_user):
    users = User.query.all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at.isoformat()
        })
    return jsonify(result), 200

@admin_bp.route('/approve-doctor/<int:user_id>', methods=['POST'])
@token_required
@roles_required('admin')
def approve_doctor(current_user, user_id):
    user = User.query.get(user_id)
    if not user or user.role != 'doctor':
        return jsonify({"error": "Doctor not found"}), 404
        
    user.status = 'active'
    db.session.commit()
    return jsonify({"message": f"Doctor {user.name} approved"}), 200

@admin_bp.route('/suspend-user/<int:user_id>', methods=['POST'])
@token_required
@roles_required('admin')
def suspend_user(current_user, user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    user.status = 'suspended'
    db.session.commit()
    return jsonify({"message": f"User {user.name} suspended"}), 200

@admin_bp.route('/stats', methods=['GET'])
@token_required
@roles_required('admin')
def get_system_stats(current_user):
    total_users = User.query.count()
    total_patients = User.query.filter_by(role='patient').count()
    total_doctors = User.query.filter_by(role='doctor').count()
    total_analyses = PatientAnalysis.query.count()
    pending_doctors = User.query.filter_by(role='doctor', status='pending_approval').count()
    
    return jsonify({
        "total_users": total_users,
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_analyses": total_analyses,
        "pending_doctors": pending_doctors
    }), 200
