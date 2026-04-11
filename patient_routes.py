from flask import Blueprint, request, jsonify
from models import db, User, PatientProfile, PatientAnalysis, Appointment, ChatMessage
from middleware import token_required, roles_required
from datetime import datetime

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/profile', methods=['GET'])
@token_required
@roles_required('patient')
def get_patient_profile(current_user):
    profile = current_user.patient_profile
    if not profile:
        return jsonify({"message": "No profile found"}), 404

    return jsonify({
        "patient_id": profile.patient_id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "age": profile.age,
        "gender": profile.gender,
        "address": profile.address
    }), 200

@patient_bp.route('/profile', methods=['POST'])
@token_required
@roles_required('patient')
def update_patient_profile(current_user):
    data = request.get_json()
    profile = current_user.patient_profile
    
    current_user.name = data.get('name', current_user.name)
    current_user.phone = data.get('phone', current_user.phone)
    
    if profile:
        profile.age = data.get('age', profile.age)
        profile.gender = data.get('gender', profile.gender)
        profile.address = data.get('address', profile.address)
    
    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200

@patient_bp.route('/analysis/history', methods=['GET'])
@token_required
@roles_required('patient')
def get_analysis_history(current_user):
    analyses = PatientAnalysis.query.filter_by(patient_user_id=current_user.id).order_by(PatientAnalysis.created_at.desc()).all()
    
    results = []
    for a in analyses:
        results.append({
            "id": a.id,
            "image_url": a.image_url,
            "severity": a.severity_label,
            "condition": a.condition_name,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "doctor_notes": a.doctor_notes
        })
    
    return jsonify(results), 200

@patient_bp.route('/analysis/<int:id>', methods=['GET'])
@token_required
@roles_required('patient')
def get_analysis_detail(current_user, id):
    analysis = PatientAnalysis.query.get(id)
    if not analysis or analysis.patient_user_id != current_user.id:
        return jsonify({"error": "Analysis not found"}), 404
        
    return jsonify({
        "id": analysis.id,
        "patient_id": current_user.patient_profile.patient_id if current_user.patient_profile else "PAT-001",
        "patient_name": current_user.name,
        "condition": analysis.condition_name or "Healthy / Minimal Bone Loss",
        "severity": analysis.severity_label or "Mild",
        "bone_loss_mm": analysis.bone_loss_mm or 0,
        "bone_loss_percent": round((analysis.bone_loss_mm / 10.0) * 100, 1) if analysis.bone_loss_mm else 0,
        "inflammation": "Minimal", # Derived or mocked per UI design
        "severity_percent": 12.0, # Mocked per image for high-fidelity demo
        "date": analysis.created_at.strftime('%Y-%m-%d'),
        "notes": analysis.doctor_notes or "",
        "image_url": analysis.image_url
    }), 200

@patient_bp.route('/appointments', methods=['GET'])
@token_required
@roles_required('patient')
def get_appointments(current_user):
    appts = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.appointment_date.asc()).all()
    results = []
    for a in appts:
        results.append({
            "id": a.id,
            "date": a.appointment_date.isoformat(),
            "doctor_id": a.doctor_id,
            "reason": a.reason,
            "status": a.status
        })
    return jsonify(results), 200

@patient_bp.route('/book-appointment', methods=['POST'])
@token_required
@roles_required('patient')
def book_appointment(current_user):
    data = request.get_json()
    try:
        new_appt = Appointment(
            patient_id=current_user.id,
            doctor_id=data.get('doctor_id'), # Should be selectable in UI
            appointment_date=datetime.fromisoformat(data.get('date')),
            reason=data.get('reason'),
            status='PENDING'
        )
        db.session.add(new_appt)
        db.session.commit()
        return jsonify({"message": "Appointment booked", "id": new_appt.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@patient_bp.route('/reports-data', methods=['GET'])
@token_required
@roles_required('patient')
def get_patient_reports(current_user):
    analyses = PatientAnalysis.query.filter_by(patient_user_id=current_user.id).order_by(PatientAnalysis.created_at.asc()).all()
    
    # Bone loss trends
    trends = []
    for a in analyses:
        trends.append({
            "date": a.created_at.strftime('%Y-%m-%d'),
            "bone_loss": a.bone_loss_mm or 0,
            "severity": a.severity_label or 'N/A'
        })
        
    latest_severity = analyses[-1].severity_label if analyses else 'Stable'
    avg_bone_loss = round(sum([a.bone_loss_mm or 0 for a in analyses]) / len(analyses), 2) if analyses else 0
    
    return jsonify({
        "bone_loss_trend": trends,
        "latest_severity": latest_severity,
        "average_bone_loss": avg_bone_loss,
        "total_scans": len(analyses)
    }), 200

