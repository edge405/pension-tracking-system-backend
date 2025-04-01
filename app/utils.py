from app import db
from datetime import datetime, date
from .models import SchedulePayout, Admin


def convert_to_date(date_str, format='%Y-%m-%d'):
    return datetime.strptime(date_str, format).date()

def update_released_payout():
    try:

        current_time = datetime.utcnow()
        released_payout = SchedulePayout.query.filter(SchedulePayout.payout_date < current_time).all()
        
        for payout in released_payout:
            payout.status = 'released'
        
        if released_payout:
            db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Error updating status: {str(e)}")

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))