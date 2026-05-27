from flask import Flask
from flask_migrate import Migrate

from app.models.database import db
from app.api.webhook import webhook_bp
from app.services.oauth import oauth_bp, fb_bp

import os
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    db.init_app(app)
    migrate = Migrate(app, db)

    with app.app_context():
        db.create_all()

    app.register_blueprint(oauth_bp)
    app.register_blueprint(fb_bp)
    app.register_blueprint(webhook_bp)
    return app
