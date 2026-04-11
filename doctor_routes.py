from flask import Blueprint, request, jsonify
from models import db, User, PatientProfile, DoctorProfile, PatientAnalysis, Appointment
from middleware import token_required, roles_required
from datetime import datetime

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/profile', methods=['GET'])
@token_required
@roles_required('doctor')
def get_profile(current_user):
    profile = current_user.doctor_profile
    return jsonify({
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "license_number": profile.license_number,
        "speciality": profile.speciality,
        "hospital_name": profile.hospital_name,
        "bio": profile.bio
    }), 200

@doctor_bp.route('/profile', methods=['PUT'])
@token_required
@roles_required('doctor')
def update_profile(current_user):
    data = request.get_json()
    profile = current_user.doctor_profile
    
    current_user.name = data.get('name', current_user.name)
    current_user.phone = data.get('phone', current_user.phone)
    
    if profile:
        profile.speciality = data.get('speciality', profile.speciality)
        profile.hospital_name = data.get('hospital_name', profile.hospital_name)
        profile.license_number = data.get('license_number', profile.license_number)
        profile.bio = data.get('bio', profile.bio)
    
    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200

@doctor_bp.route('/dashboard-stats', methods=['GET'])
@token_required
@roles_required('doctor')
def get_dashboard_stats(current_user):
    # Total assigned patients
    total_patients = PatientProfile.query.filter_by(assigned_doctor_id=current_user.id).count()
    
    # High risk scans (e.g., severity > 70 or alert flag)
    # Since I removed the 'alert' field and unified predictions, I'll filter by severity label if available
    high_risk = PatientAnalysis.query.filter(
        PatientAnalysis.doctor_user_id == current_user.id,
        PatientAnalysis.severity_label.in_(['High', 'Critical'])
    ).count()
    
    # Scans today
    today = datetime.utcnow().date()
    scans_today = PatientAnalysis.query.filter(
        PatientAnalysis.doctor_user_id == current_user.id,
        db.func.date(PatientAnalysis.created_at) == today
    ).count()

    # Recent scans for the list
    recent_analyses = PatientAnalysis.query.filter_by(doctor_user_id=current_user.id)\
        .order_by(PatientAnalysis.created_at.desc()).limit(10).all()
        
    recent_list = []
    for a in recent_analyses:
        patient = User.query.get(a.patient_user_id)
        recent_list.append({
            "id": a.id,
            "patient_name": patient.name if patient else "Unknown",
            "patient_id": patient.patient_profile.patient_id if patient and patient.patient_profile else "N/A",
            "severity": a.severity_label,
            "condition": a.condition_name,
            "date": a.created_at.isoformat(),
            "status": a.status
        })

    return jsonify({
        "active_patients": total_patients,
        "high_risk": high_risk,
        "scans_today": scans_today,
        "recent_scans": recent_list
    }), 200

@doctor_bp.route('/patients', methods=['GET'])
@token_required
@roles_required('doctor')
def get_my_patients(current_user):
    patients = User.query.join(PatientProfile, User.id == PatientProfile.user_id)\
        .filter(PatientProfile.assigned_doctor_id == current_user.id).all()
    
    result = []
    for p in patients:
        result.append({
            "id": p.id,
            "name": p.name,
            "patient_id": p.patient_profile.patient_id,
            "email": p.email
        })
    return jsonify(result), 200

@doctor_bp.route('/diagnose', methods=['POST'])
@token_required
@roles_required('doctor')
def add_diagnosis(current_user):
    data = request.get_json()
    analysis_id = data.get('analysis_id')
    analysis = PatientAnalysis.query.get(analysis_id)
    
    if not analysis or analysis.doctor_user_id != current_user.id:
        return jsonify({"error": "Analysis not found or unauthorized"}), 404
        
    analysis.status = data.get('status', 'APPROVED')
    analysis.doctor_notes = data.get('notes')
    analysis.condition_name = data.get('condition_name', analysis.condition_name)
    
    db.session.commit()
    return jsonify({"message": "Diagnosis saved"}), 200

@doctor_bp.route('/appointments', methods=['GET'])
@token_required
@roles_required('doctor')
def get_appointments(current_user):
    appts = Appointment.query.filter_by(doctor_id=current_user.id).order_by(Appointment.appointment_date.asc()).all()
    results = []
    for a in appts:
        patient = User.query.get(a.patient_id)
        results.append({
            "id": a.id,
            "date": a.appointment_date.isoformat(),
            "patient_name": patient.name if patient else "Unknown",
            "reason": a.reason,
            "status": a.status
        })
    return jsonify(results), 200

@doctor_bp.route('/appointments/<int:id>/confirm', methods=['PUT'])
@token_required
@roles_required('doctor')
def confirm_appointment(current_user, id):
    appt = Appointment.query.get(id)
    if not appt or appt.doctor_id != current_user.id:
        return jsonify({"error": "Appointment not found"}), 404
    
    appt.status = 'CONFIRMED'
    db.session.commit()
    return jsonify({"message": "Appointment confirmed"}), 200

@doctor_bp.route('/analysis/<int:id>', methods=['GET'])
@token_required
@roles_required('doctor')
def get_analysis_detail_doctor(current_user, id):
    analysis = PatientAnalysis.query.get(id)
    if not analysis or analysis.doctor_user_id != current_user.id:
        return jsonify({"error": "Analysis not found"}), 404
        
    patient = User.query.get(analysis.patient_user_id)
    
    return jsonify({
        "id": analysis.id,
        "patient_id": patient.patient_profile.patient_id if patient and patient.patient_profile else "PAT-001",
        "patient_name": patient.name if patient else "Unknown",
        "condition": analysis.condition_name or "Healthy / Minimal Bone Loss",
        "severity": analysis.severity_label or "Mild",
        "bone_loss_mm": analysis.bone_loss_mm or 0,
        "bone_loss_percent": round((analysis.bone_loss_mm / 10.0) * 100, 1) if analysis.bone_loss_mm else 0,
        "inflammation": "Minimal",
        "severity_percent": 12.0,
        "date": analysis.created_at.strftime('%Y-%m-%d'),
        "notes": analysis.doctor_notes or "",
        "image_url": analysis.image_url
    }), 200

@doctor_bp.route('/patient-history/<int:uid>', methods=['GET'])
@token_required
@roles_required('doctor')
def get_patient_history(current_user, uid):
    # Verify the patient is assigned to this doctor
    patient_profile = PatientProfile.query.filter_by(user_id=uid, assigned_doctor_id=current_user.id).first()
    if not patient_profile:
        return jsonify({"error": "Patient not found or unauthorized"}), 404
        
    analyses = PatientAnalysis.query.filter_by(patient_user_id=uid).order_by(PatientAnalysis.created_at.desc()).all()
    
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
    
@doctor_bp.route('/reports-data', methods=['GET'])
@token_required
@roles_required('doctor')
def get_reports_data(current_user):
    # Severity stats
    severity_map = {'Mild': 0, 'Moderate': 0, 'High': 0, 'Critical': 0}
    analyses = PatientAnalysis.query.filter_by(doctor_user_id=current_user.id).all()
    
    total_bone_loss = 0
    count_with_bone_loss = 0
    
    for a in analyses:
        label = a.severity_label or 'Moderate' # Fallback
        if label in severity_map:
            severity_map[label] += 1
        
        if a.bone_loss_mm is not None:
            total_bone_loss += a.bone_loss_mm
            count_with_bone_loss += 1
            
    avg_bone_loss = round(total_bone_loss / count_with_bone_loss, 2) if count_with_bone_loss > 0 else 0
    
    # Simple trend extraction (last 7 days of scans)
    # In a real app, this would be grouped by date
    recent_trend = []
    # (Simplified for now: count per day for the last month)
    # Using a quick manual grouping
    trend_dict = {}
    for a in analyses:
        d = a.created_at.strftime('%Y-%m-%d')
        trend_dict[d] = trend_dict.get(d, 0) + 1
    
    # Sort and take last 10 days
    sorted_trend = sorted(trend_dict.items())[-10:]
    recent_trend = [{"date": k, "count": v} for k, v in sorted_trend]
    
    return jsonify({
        "severity_stats": severity_map,
        "average_bone_loss": avg_bone_loss,
        "total_scans": len(analyses),
        "trends": recent_trend
    }), 200
