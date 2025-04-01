from datetime import datetime
from sqlalchemy.orm import relationship
from app import db
from flask_jwt_extended import create_access_token, decode_token
import bcrypt

class Pensioner(db.Model):
    __tablename__ = 'pensioners'
    
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(255), nullable=False)
    senior_citizen_id = db.Column(db.String(50), unique=True, nullable=False)
    contact_number = db.Column(db.String(20))
    sex = db.Column(db.String(10))
    address = db.Column(db.Text)
    birthdate = db.Column(db.Date)
    password = db.Column(db.String(128))
    valid_id = db.Column(db.String(255))
    payout_amount = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Fixed the cascade configuration
    payments = relationship('PaymentHistory', back_populates='pensioner', cascade="all, delete")
    notifications = relationship('Notification', back_populates='pensioner', cascade="all, delete")

    def verify_password(self, password):
        """Verify if the provided password matches the stored hashed password."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

    @staticmethod
    def hash_password(password):
        """Hash a password using bcrypt and return the hashed password as a string."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        try:
            decoded_token = decode_token(token)
            id = decoded_token.get("sub")
            print("-------", id)
            return Pensioner.query.get(id) if id else None
        except Exception:
            return None

    def generate_auth_token(self, expires_delta=None):
        """
        Generate a JWT token for the user.
        The token contains all the pensioner's fields as additional claims.
        """
        additional_claims = {
            "id": self.id,
            "fullname": self.fullname,
            "senior_citizen_id": self.senior_citizen_id,
            "contact_number": self.contact_number,
            "address": self.address,
            "birthdate": str(self.birthdate) if self.birthdate else None,
            "valid_id": self.valid_id,
            "payout_amount": float(self.payout_amount) if self.payout_amount else None,
            "status": self.status,
            "created_at": str(self.created_at) if self.created_at else None,
            "user_type": "pensioner"
        }
        
        return create_access_token(
            identity=str(self.id), 
            expires_delta=expires_delta, 
            additional_claims=additional_claims
        )
    
    def to_dict(self):
        """Convert the Pensioner object to a dictionary."""
        return {
            "id": self.id,
            "fullname": self.fullname,
            "senior_citizen_id": self.senior_citizen_id,
            "contact_number": self.contact_number,
            "address": self.address,
            "birthdate": str(self.birthdate) if self.birthdate else None,
            "valid_id": self.valid_id,
            "payout_amount": float(self.payout_amount) if self.payout_amount else None,
            "status": self.status,
            "created_at": str(self.created_at) if self.created_at else None
        }


class Admin(db.Model):
    __tablename__ = 'admin'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def verify_password(self, password):
        """Verify if the provided password matches the stored hashed password."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

    @staticmethod
    def hash_password(password):
        """Hash a password using bcrypt and return the hashed password as a string."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        """
        Verify a JWT token and return the corresponding admin.
        If the token is invalid or expired, return None.
        """
        try:
            decoded_token = decode_token(token)
            id = decoded_token.get("sub")

            return Admin.query.get(id) if id else None
        except Exception:
            return None

    def generate_auth_token(self, expires_delta=None):
        """
        Generate a JWT token for the admin.
        The token contains all the admin's fields as additional claims.
        """
        additional_claims = {
            "id": self.id,
            "username": self.username,
            "created_at": str(self.created_at) if self.created_at else None,
            "user_type": "admin"
        }
        
        return create_access_token(
            identity=str(self.id), 
            expires_delta=expires_delta, 
            additional_claims=additional_claims
        )
    
class SchedulePayout(db.Model):
    __tablename__ = 'schedule_payout'
    
    schedule_id = db.Column(db.Integer, primary_key=True)
    payout_date = db.Column(db.DateTime, default=datetime.utcnow)
    payout_location = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    # Fixed the cascade configuration
    payments = relationship('PaymentHistory', back_populates='schedule', cascade="all, delete")


class PaymentHistory(db.Model):
    __tablename__ = 'payment_history'

    id = db.Column(db.Integer, primary_key=True)
    pensioner_id = db.Column(db.Integer, db.ForeignKey('pensioners.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule_payout.schedule_id'), nullable=False)
    payout_amount = db.Column(db.Float, nullable=False)  # Store the actual payout amount
    status = db.Column(db.String(50), default='scheduled')  # e.g., 'scheduled', 'released'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Removed incorrect cascade configuration from child relationships
    schedule = relationship('SchedulePayout', back_populates='payments')
    pensioner = relationship('Pensioner', back_populates='payments')

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    pensioner_id = db.Column(db.Integer, db.ForeignKey('pensioners.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    location = db.Column(db.Text, nullable=False)
    time = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pensioner = relationship('Pensioner', back_populates='notifications')