from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import logging

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")
    
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

    from .pensioner_routes import pensioner_bp
    from .admin_routes import admin_bp
    app.register_blueprint(pensioner_bp, url_prefix='/api/pensioner')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    from app.models import Pensioner,  Admin, SchedulePayout, PaymentHistory, Notification

    if not app.debug:
        logging.basicConfig(level=logging.INFO)
        handler = logging.StreamHandler()
        file_handler = logging.FileHandler('app.log')
        
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        
        handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        app.logger.addHandler(handler)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Pension Tracking System Backend')

    return app