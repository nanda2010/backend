import os
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from flask import Flask, send_from_directory, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv
from models import db, User, ChatMessage, Notification, bcrypt

load_dotenv()

def create_app():
    # Environment Configuration
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    app = Flask(__name__)
    
    # Database Configuration (Environment-First with SQLite fallback)
    db_path = os.path.join(root_dir, 'perioguard.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f"sqlite:///{db_path}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'perioguard-titanium-secret-2026')
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    # Enable global CORS for production-ready cross-origin requests
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    
    # Minimal AI Demo Route as requested for quick validation
    @app.route('/api/analyze', methods=['POST'])
    def analyze_demo():
        return jsonify({
            "result": "Healthy",
            "confidence": "92%"
        })
    
    # Initialize SocketIO for real-time syncing
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

    from auth_routes import auth_bp
    from doctor_routes import doctor_bp
    from patient_routes import patient_bp
    from ai_routes import ai_bp

    # Register API Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(doctor_bp, url_prefix='/api/doctor')
    app.register_blueprint(patient_bp, url_prefix='/api/patient')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')

    @app.route('/')
    def home():
        return "PerioGuard AI Backend Running ✅"

    @app.before_request
    def log_request_info():
        if request.path.startswith('/api/'):
            logger.info(f"API Request: {request.method} {request.path}")

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Real-time WebSocket Handlers
    @socketio.on('connect')
    def handle_connect():
        print(f"SUCCESS: Client Connected: {request.sid}")

    @socketio.on('join')
    def on_join(data):
        room = data['user_id']
        join_room(room)
        print(f"INFO: User {room} joined clinical room")

    @socketio.on('send_message')
    def handle_message(data):
        # Broadcast message to specific receiver room
        emit('new_message', data, room=data['receiver_id'])
        
        # Save to DB (simplified for plan)
        with app.app_context():
            new_msg = ChatMessage(
                sender_id=data['sender_id'],
                receiver_id=data['receiver_id'],
                message=data['message']
            )
            db.session.add(new_msg)
            db.session.commit()

    @socketio.on('notify')
    def handle_notification(data):
        emit('notification', data, room=data['user_id'])

    with app.app_context():
        db.create_all()
        # Self-Healing: Auto-Activate all users for development straight access
        User.query.update({User.status: 'active'})
        db.session.commit()
        print("SUCCESS: Clinical Sync: All accounts activated and ready for straight login.")
    
    app.socketio = socketio # Attach for use in routes
    return app, socketio

# Instantiate for Gunicorn usage
app, socketio = create_app()

if __name__ == '__main__':
    print("\nSYSTEM: PerioGuard AI Enterprise Engine Running")
    print("SYNC: Real-time Sync Active")
    # Bind to 0.0.0.0 and use Render's dynamic port
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, debug=True, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
