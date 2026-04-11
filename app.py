import os
import sys
import logging

# ── Path Fix: Ensure the backend directory is always on sys.path,
#    regardless of the CWD Gunicorn / Render sets at runtime.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── Eventlet monkey-patch MUST happen before any other imports
import eventlet
eventlet.monkey_patch()

# ── Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from flask import Flask, send_from_directory, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)

    # ── Database Configuration
    db_path = os.path.join(BACKEND_DIR, 'perioguard.db')
    database_url = os.getenv('DATABASE_URL', f"sqlite:///{db_path}")

    # Render's Postgres URLs start with "postgres://" — SQLAlchemy needs "postgresql://"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'perioguard-titanium-secret-2026')
    app.config['UPLOAD_FOLDER'] = os.path.join(BACKEND_DIR, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Extensions
    from models import db, bcrypt
    db.init_app(app)
    bcrypt.init_app(app)

    # ── CORS – allow all origins for API cross-origin access
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # ── SocketIO with eventlet (required for Gunicorn -k eventlet)
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        logger=False,
        engineio_logger=False
    )

    # ── Import and register Blueprints INSIDE create_app (avoids circular imports)
    from auth_routes import auth_bp
    from doctor_routes import doctor_bp
    from patient_routes import patient_bp
    from ai_routes import ai_bp
    from admin_routes import admin_bp

    app.register_blueprint(auth_bp,    url_prefix='/api/auth')
    app.register_blueprint(doctor_bp,  url_prefix='/api/doctor')
    app.register_blueprint(patient_bp, url_prefix='/api/patient')
    app.register_blueprint(ai_bp,      url_prefix='/api/ai')
    app.register_blueprint(admin_bp,   url_prefix='/api/admin')

    # ── Inline demo / health routes
    @app.route('/')
    def home():
        return jsonify({"status": "online", "service": "PerioGuard AI Backend ✅"})

    @app.route('/health')
    def health():
        return jsonify({"status": "healthy"}), 200

    @app.route('/api/analyze', methods=['POST'])
    def analyze_demo():
        return jsonify({"result": "Healthy", "confidence": "92%"})

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.before_request
    def log_request_info():
        if request.path.startswith('/api/'):
            logger.info("API %s %s", request.method, request.path)

    # ── WebSocket handlers
    from models import ChatMessage

    @socketio.on('connect')
    def handle_connect():
        logger.info("Client connected: %s", request.sid)

    @socketio.on('join')
    def on_join(data):
        room = str(data.get('user_id', ''))
        join_room(room)
        logger.info("User %s joined room", room)

    @socketio.on('send_message')
    def handle_message(data):
        emit('new_message', data, room=str(data.get('receiver_id', '')))
        with app.app_context():
            from models import db as _db
            new_msg = ChatMessage(
                sender_id=data['sender_id'],
                receiver_id=data['receiver_id'],
                message=data['message']
            )
            _db.session.add(new_msg)
            _db.session.commit()

    @socketio.on('notify')
    def handle_notification(data):
        emit('notification', data, room=str(data.get('user_id', '')))

    # ── DB Init
    with app.app_context():
        from models import db as _db, User
        _db.create_all()
        # Auto-activate all users (straight-access mode)
        try:
            User.query.update({User.status: 'active'})
            _db.session.commit()
            logger.info("Clinical Sync: All accounts activated.")
        except Exception as exc:
            _db.session.rollback()
            logger.warning("Auto-activate skipped: %s", exc)

    app.socketio = socketio
    return app, socketio


# ── Expose module-level `app` and `socketio` for Gunicorn (`gunicorn app:app`)
app, socketio = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    logger.info("PerioGuard AI starting on port %d", port)
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
