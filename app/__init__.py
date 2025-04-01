from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import logging
import os

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    static_folder = os.path.join(os.path.dirname(base_dir), 'static')

    app = Flask(__name__, 
                static_folder=static_folder,
                static_url_path='/static')
    app.config.from_object("config.Config")

    os.makedirs(static_folder, exist_ok=True)
    os.makedirs(os.path.join(static_folder, 'uploads'), exist_ok=True)
    
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