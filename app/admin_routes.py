from flask import g, Blueprint, jsonify, request
from flask_httpauth import HTTPBasicAuth
from sqlalchemy import desc
from datetime import datetime, timedelta, date
from app import db
from .models import Admin, Pensioner, PaymentHistory, SchedulePayout, Notification
from .utils import convert_to_date, update_released_payout, calculate_age

auth = HTTPBasicAuth()
admin_bp = Blueprint('admin', __name__)

@auth.verify_password
def verify_password(username_or_token, password):
    # Try to authenticate by token
    user = Admin.verify_auth_token(username_or_token)
    if not user:
        # If token authentication fails, try username/password authentication
        user = Admin.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    g.user.user_type = 'admin'
    return True

@admin_bp.route('/login', methods=['GET'])
@auth.login_required
def admin_login():
    """Login for admin users."""
    admin = g.user

    # Generate access token
    expires = timedelta(hours=6)
    access_token = admin.generate_auth_token(expires_delta=expires)
    
    return jsonify({
        'access_token': access_token,
        'expires_in': expires.total_seconds(),
        'user_id': admin.id,
        'username': admin.username,
        'user_type': 'admin'
    }), 200

@admin_bp.route('/register', methods=['POST'])
def register_pensioner():
    """Register a new pensioner."""
    data = request.json
    
    # Validate required fields
    required_fields = ['username', 'password']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if senior_citizen_id already exists
    existing_pensioner = Admin.query.filter_by(username=data['username']).first()
    if existing_pensioner:
        return jsonify({'error': 'Admin already registered'}), 409

    
    # Create new pensioner
    admin = Admin(
        username = data['username'],
        password = Admin.hash_password(data['password'])
    )
    
    try:
        db.session.add(admin)
        db.session.commit()
    
        
        return jsonify({
            "success": True,
            'message': 'Admin registered successfully.',
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



# ===========================================
# Pensioner Management Routes
# ===========================================
@admin_bp.route('/pending-pensioners', methods=['GET'])
@auth.login_required
def get_pending_pensioners():
    """Get all pending pensioners."""
    
    # Check if the user is an admin
    if g.user.user_type != 'admin':
        return jsonify({'error': 'Access denied. Admin only.'}), 403
    
    pending_pensioners = Pensioner.query.filter_by(status='pending').all()
    
    
    result = []
    for pensioner in pending_pensioners:
        age = calculate_age(pensioner.birthdate) if pensioner.birthdate else None
        result.append({
            'id': pensioner.id,
            'fullname': pensioner.fullname,
            'senior_citizen_id': pensioner.senior_citizen_id,
            'sex': pensioner.sex,
            'contact_number': pensioner.contact_number,
            'address': pensioner.address,
            'age': age,
            'civil_status': pensioner.civil_status,
            'birthdate': pensioner.birthdate.strftime('%Y-%m-%d') if pensioner.birthdate else None,
            'valid_id': pensioner.valid_id,
            'created_at': pensioner.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': pensioner.status,
            'payout_amount': float(pensioner.payout_amount) if pensioner.payout_amount else None,
        })
    
    return jsonify(result), 200

@admin_bp.route('/approved-pensioners', methods=['GET'])
@auth.login_required
def get_approved_pensioners():
    """Get all approved pensioners."""
    
    # Check if the user is an admin
    if g.user.user_type != 'admin':
        return jsonify({'error': 'Access denied. Admin only.'}), 403
    
    approved_pensioners = Pensioner.query.filter_by(status='approved').all()
    
    result = []
    for pensioner in approved_pensioners:
        age = calculate_age(pensioner.birthdate) if pensioner.birthdate else None
        result.append({
            'id': pensioner.id,
            'fullname': pensioner.fullname,
            'senior_citizen_id': pensioner.senior_citizen_id,
            'sex': pensioner.sex,
            'contact_number': pensioner.contact_number,
            'address': pensioner.address,
            'age': age,
            'civil_status': pensioner.civil_status,
            'birthdate': pensioner.birthdate.strftime('%Y-%m-%d') if pensioner.birthdate else None,
            'valid_id': pensioner.valid_id,
            'payout_amount': float(pensioner.payout_amount) if pensioner.payout_amount else None,
            'created_at': pensioner.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': pensioner.status,
            'payout_amount': float(pensioner.payout_amount) if pensioner.payout_amount else None,
        })
    
    return jsonify(result), 200

@admin_bp.route('/get-pensioners/<int:pensioner_id>', methods=['GET'])
@auth.login_required
def get_pensioner_details(pensioner_id):
    """Get detailed information for a specific pensioner."""
    
    # Check if the user is an admin
    if g.user.user_type != 'admin':
        return jsonify({'error': 'Access denied. Admin only.'}), 403
    
    pensioner = Pensioner.query.get(pensioner_id)
    
    if not pensioner:
        return jsonify({'error': 'Pensioner not found'}), 404
        
    return jsonify({
        'id': pensioner.id,
        'fullname': pensioner.fullname,
        'senior_citizen_id': pensioner.senior_citizen_id,
        'sex': pensioner.sex,
        'contact_number': pensioner.contact_number,
        'address': pensioner.address,
        'birthdate': pensioner.birthdate.strftime('%Y-%m-%d') if pensioner.birthdate else None,
        'valid_id': pensioner.valid_id,
        'payout_amount': float(pensioner.payout_amount) if pensioner.payout_amount else None,
        'status': pensioner.status,
        'created_at': pensioner.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }), 200

@admin_bp.route('/pensioners/<int:pensioner_id>/status', methods=['PUT'])
@auth.login_required
def update_pensioner_status(pensioner_id):
    """Update the status of a pensioner."""
    
    # Check if the user is an admin
    if g.user.user_type != 'admin':
        return jsonify({'error': 'Access denied. Admin only.'}), 403
    
    pensioner = Pensioner.query.get(pensioner_id)
    
    if not pensioner:
        return jsonify({'error': 'Pensioner not found'}), 404
    
    data = request.json
    
    if 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
    
    # Only allow valid status values
    if data['status'] not in ['pending', 'approved', 'rejected']:
        return jsonify({'error': 'Invalid status value'}), 400
    
    pensioner.status = data['status']
    
    # Set payout amount if provided and status is approved
    if data['status'] == 'approved' and 'payout_amount' in data:
        try:
            pensioner.payout_amount = float(data['payout_amount'])
        except ValueError:
            return jsonify({'error': 'Invalid payout amount value'}), 400
    
    pensioner.created_at = date.today()
    # Save changes
    db.session.commit()
    
    # # Create notification
    # notification = Notification(
    #     message=f"Pensioner {pensioner.fullname}'s application has been {data['status']}."
    # )
    # db.session.add(notification)
    # db.session.commit()
    
    return jsonify({'message': 'Pensioner status updated successfully'}), 200

@admin_bp.route('/pensioners/<int:pensioner_id>/payout', methods=['PUT'])
@auth.login_required
def update_pensioner_payout(pensioner_id):
    """Update the payout amount for a specific pensioner."""
    
    # Check if the user is an admin
    if g.user.user_type != 'admin':
        return jsonify({'error': 'Access denied. Admin only.'}), 403
    
    pensioner = Pensioner.query.get(pensioner_id)
    
    if not pensioner:
        return jsonify({'error': 'Pensioner not found'}), 404
    
    data = request.json
    
    if 'payout_amount' not in data:
        return jsonify({'error': 'Payout amount is required'}), 400
    
    try:
        pensioner.payout_amount = float(data['payout_amount'])
        db.session.commit()
        
        return jsonify({
            'message': 'Payout amount updated successfully'
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid payout amount'}), 400

# ===========================================
# Schedule Payout Routes
# ===========================================
@admin_bp.route('/schedule-payout', methods=['POST'])
@auth.login_required
def create_schedule_payout():
    """Create a new schedule payout."""
    if g.user.user_type != 'admin':
        return jsonify({'error': 'Access denied. Admin only.'}), 403

    data = request.json
    required_fields = ['payout_date', 'payout_location', 'start_time', 'end_time']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    try:
        # Parse date and times
        payout_date = convert_to_date(data['payout_date'])
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()

        # Create new schedule
        schedule = SchedulePayout(
            payout_date=payout_date,
            payout_location=data['payout_location'],
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(schedule)
        db.session.commit()

        # Add payment history entries and notifications for approved pensioners
        approved_pensioners = Pensioner.query.filter_by(status='approved').all()
        for pensioner in approved_pensioners:
            # Store the pensioner's current payout amount in the payment history
            payment = PaymentHistory(
                pensioner_id=pensioner.id,
                schedule_id=schedule.schedule_id,
                payout_amount=pensioner.payout_amount  # Use the current payout amount
            )
            db.session.add(payment)

            # Create notification for the pensioner
            formatted_date = payout_date.strftime('%B %d, %Y')
            formatted_start_time = datetime.strptime(data['start_time'], '%H:%M').strftime('%I:%M %p')
            formatted_end_time = datetime.strptime(data['end_time'], '%H:%M').strftime('%I:%M %p')
            formatted_time_range = f"{formatted_start_time} - {formatted_end_time}"

            notification = Notification(
                pensioner_id=pensioner.id,
                message=f"Your next pension payment is scheduled for {formatted_date} at {data['payout_location']} from {formatted_time_range}.",
                location=data['payout_location'],
                time=formatted_time_range,
                date=payout_date
            )
            db.session.add(notification)

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Schedule payout created successfully',
            'schedule_id': schedule.schedule_id
        }), 201
    except ValueError:
        return jsonify({'error': 'Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time'}), 400

@admin_bp.route('/schedule-payout', methods=['GET'])
@auth.login_required
def get_schedule_payouts():
    """Get all schedule payouts."""
    
    update_released_payout()

    # Check if the user is an admin
    if g.user.user_type != 'admin':
        return jsonify({'error': 'Access denied. Admin only.'}), 403
    
    schedules = SchedulePayout.query.order_by(desc(SchedulePayout.payout_date)).all()
    total_pensioners = Pensioner.query.count()
    result = []
    for schedule in schedules:
        result.append({
            'schedule_id': schedule.schedule_id,
            'payout_date': schedule.payout_date.strftime('%Y-%m-%d'),
            'payout_location': schedule.payout_location,
            'start_time': schedule.start_time.strftime('%H:%M'),
            'status': schedule.status,
            'total_pensioners': total_pensioners,
            'end_time': schedule.end_time.strftime('%H:%M')
        })
    
    return jsonify(result), 200

@admin_bp.route('/system-alert', methods=['GET'])
@auth.login_required
def system_alert():
    """Get system alert with pension payout schedule and total pending pensioners."""

    update_released_payout()
    
    # Check if the user is an admin
    if g.user.user_type != 'admin':
        return jsonify({'error': 'Access denied. Admin only.'}), 403

    try:
        # Query all scheduled payouts
        schedules = SchedulePayout.query.filter_by(status='scheduled').all()

        # Serialize the schedule payout data
        schedule_data = [
            {
                "schedule_id": schedule.schedule_id,
                "payout_date": schedule.payout_date.strftime('%Y-%m-%d'),
                "payout_location": schedule.payout_location,
                "start_time": schedule.start_time.strftime('%H:%M'),
                "end_time": schedule.end_time.strftime('%H:%M'),
                "status": schedule.status
            }
            for schedule in schedules
        ]

        # Query total pending pensioners
        pending_pensioners_count = Pensioner.query.filter_by(status='pending').count()
        all_pensioner = Pensioner.query.all()

        # Prepare the response
        response = {
            "payout_schedules": schedule_data,
            "total_pending_pensioners": pending_pensioners_count,
            "total_pensioners": len(all_pensioner)
        }

        return jsonify(response), 200

    except Exception as e:
        # Log the error (optional: use a logging library)
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": "An unexpected error occurred."}), 500