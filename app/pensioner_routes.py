from flask import g, Blueprint, jsonify, request
from flask_httpauth import HTTPBasicAuth
from sqlalchemy import desc
from datetime import datetime,date, timedelta
from app import db
from .models import Pensioner, PaymentHistory, SchedulePayout, Notification
from .utils import convert_to_date, calculate_age
from .imageUpload import upload_image

auth = HTTPBasicAuth()
pensioner_bp = Blueprint('pensioner', __name__)

@auth.verify_password
def verify_password(senior_citizen_id_or_token, password):
    # Try to authenticate by token
    user = Pensioner.verify_auth_token(senior_citizen_id_or_token)
    if not user:
        # If token authentication fails, try username/password authentication
        user = Pensioner.query.filter_by(senior_citizen_id=senior_citizen_id_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    g.user.user_type = 'pensioner'
    return True

@pensioner_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'valid_id' in request.files:
        file = request.files['valid_id']
        file_path = upload_image(file)
        
    return jsonify({
        'image_path': file_path
    })


@pensioner_bp.route('/register', methods=['POST'])
def register_pensioner():
    """Register a new pensioner."""
    # Check content type and get data accordingly
    if request.content_type and 'application/json' in request.content_type:
        # Handle JSON data
        data = request.json
        file = None
    else:
        # Handle form data
        data = request.form
        file = request.files.get('valid_id')
    
    # Validate required fields
    required_fields = ['fullname', 'senior_citizen_id', 'password']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if senior_citizen_id already exists
    existing_pensioner = Pensioner.query.filter_by(senior_citizen_id=data['senior_citizen_id']).first()
    if existing_pensioner:
        return jsonify({'error': 'ERROR! Senior citizen ID already registered.'}), 409
    
    # Process birthdate if provided
    birthdate = None
    if 'birthdate' in data and data['birthdate']:
        try:
            birthdate = convert_to_date(data['birthdate'])
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Handle file upload
    file_path = None
    if file and file.filename:
        # Handle file from form data
        file_path = upload_image(file)
    elif 'valid_id' in data and isinstance(data, dict):
        # Handle file info from JSON (assuming it contains a path or identifier)
        file_path = data['valid_id']

    # Create new pensioner
    new_pensioner = Pensioner(
        fullname=data['fullname'],
        senior_citizen_id=data['senior_citizen_id'],
        password=Pensioner.hash_password(data['password']),
        contact_number=data.get('contact_number'),
        address=data.get('address'),
        birthdate=birthdate,
        valid_id=file_path,
        status='pending'
    )
    
    try:
        db.session.add(new_pensioner)
        db.session.commit()
        
        # # Create notification for admin
        # notification = Notification(
        #     message=f"New pensioner registration: {new_pensioner.fullname} is pending approval."
        # )
        # db.session.add(notification)
        # db.session.commit()
        
        return jsonify({
            'message': 'Registration successful. Your account is pending approval.',
            'pensioner_id': new_pensioner.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@pensioner_bp.route('/login', methods=['GET'])
@auth.login_required
def login():
    """Login for pensioners."""
    
    pensioner = g.user
    
    expires = timedelta(hours=6)
    access_token = pensioner.generate_auth_token(expires_delta=expires)
    
    return jsonify({
        'token': access_token,
        'expires_in': expires.total_seconds(),
        'pensioner': pensioner.to_dict(),
        'user_type': 'pensioner'
    }), 200

    
# ===========================================
# Pensioner Profile Routes
# ===========================================
@pensioner_bp.route('/profile', methods=['GET'])
@auth.login_required
def get_profile():
    """Get the profile information of the logged-in pensioner."""
    pensioner_id = g.user.id

    # Check if the user is a pensioner
    if g.user.user_type != 'pensioner':
        return jsonify({'error': 'Access denied. Pensioners only.'}), 403

    pensioner = Pensioner.query.get(pensioner_id)

    if not pensioner:
        return jsonify({'error': 'Pensioner not found'}), 404

    # Calculate age if birthdate is available

    age = calculate_age(pensioner.birthdate) if pensioner.birthdate else None

    return jsonify({
        'id': pensioner.id,
        'fullname': pensioner.fullname,
        'senior_citizen_id': pensioner.senior_citizen_id,
        'sex': pensioner.sex,
        'contact_number': pensioner.contact_number,
        'address': pensioner.address,
        'birthdate': pensioner.birthdate.strftime('%Y-%m-%d') if pensioner.birthdate else None,
        'age': age,
        'valid_id': pensioner.valid_id,
        'payout_amount': float(pensioner.payout_amount) if pensioner.payout_amount else None,
        'status': pensioner.status,
        'created_at': pensioner.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }), 200

@pensioner_bp.route('/profile', methods=['PUT'])
@auth.login_required
def update_profile():
    """Update the profile information of the logged-in pensioner."""
    pensioner_id = g.user.id
    
    # Check if the user is a pensioner
    if g.user.user_type != 'pensioner':
        return jsonify({'error': 'Access denied. Pensioners only.'}), 403
    
    pensioner = Pensioner.query.get(pensioner_id)
    
    if not pensioner:
        return jsonify({'error': 'Pensioner not found'}), 404
    
    data = request.json
    
    # Update fields if provided in the request
    if 'fullname' in data:
        pensioner.fullname = data['fullname']
    if 'contact_number' in data:
        pensioner.contact_number = data['contact_number']
    if 'address' in data:
        pensioner.address = data['address']
    if 'birthdate' in data and data['birthdate']:
        try:
            pensioner.birthdate = convert_to_date(data['birthdate'])
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Save changes
    db.session.commit()
    
    return jsonify({'message': 'Profile updated successfully'}), 200

# ===========================================
# Payment History Routes
# ===========================================
@pensioner_bp.route('/payments-history', methods=['GET'])
@auth.login_required
def get_payments():
    """Get the payment history of the logged-in pensioner."""
    pensioner_id = g.user.id
    if g.user.user_type != 'pensioner':
        return jsonify({'error': 'Access denied. Pensioners only.'}), 403

    pensioner = Pensioner.query.get(pensioner_id)
    if not pensioner:
        return jsonify({'error': 'Pensioner not found'}), 404

    payments = (PaymentHistory.query
                .filter_by(pensioner_id=pensioner_id)
                .join(SchedulePayout)
                .order_by(desc(SchedulePayout.payout_date))
                .all())

    today = datetime.now().date()
    result = []
    for payment in payments:
        payout_date = payment.schedule.payout_date.date()
        status = "scheduled" if payout_date > today else "released"

        result.append({
            'id': payment.id,
            'schedule_id': payment.schedule_id,
            'status': status,
            'payout_date': payment.schedule.payout_date.strftime('%Y-%m-%d'),
            'payout_location': payment.schedule.payout_location,
            'payout_amount': float(payment.payout_amount),  # Use the stored payout amount
            'start_time': payment.schedule.start_time.strftime('%H:%M'),
            'end_time': payment.schedule.end_time.strftime('%H:%M')
        })

    return jsonify(result), 200

# ===========================================
# Notification Routes
# ===========================================
@pensioner_bp.route('/notifications', methods=['GET'])
@auth.login_required
def get_notifications():
    """Get all notifications for the logged-in pensioner."""
    
    # Check if the user is a pensioner
    if g.user.user_type != 'pensioner':
        return jsonify({'error': 'Access denied. Pensioners only.'}), 403
    
    # Get the logged-in pensioner's ID
    pensioner_id = g.user.id
    
    # Query notifications specifically for the logged-in pensioner
    notifications = Notification.query.filter_by(pensioner_id=pensioner_id).order_by(desc(Notification.date)).all()
    
    # Prepare the result list
    result = []
    for notification in notifications:
        result.append({
            'id': notification.id,
            'message': notification.message,
            'location': notification.location,
            'time': notification.time,
            'payout_date': notification.date.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(result), 200