from flask_sqlalchemy import SQLAlchemy
from app.base import Base

db = SQLAlchemy(model_class=Base)
