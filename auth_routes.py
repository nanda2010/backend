from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/test')
def test():
    return {"message": "Auth routes working"}
