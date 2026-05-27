import os
from dotenv import load_dotenv
from flask_migrate import Migrate
from app import create_app
from app.models.database import db

load_dotenv()

app = create_app()
migrate = Migrate(app, db)

@app.route('/')
def hello_world():
    return 'Amo-META is running! Go to /oauth/authorize?subdomain=YOUR_SUBDOMAIN to connect.'

@app.route('/privacy')
def privacy():
    return 'Privacy Policy: We protect your data and do not share it.'

@app.route('/terms')
def terms():
    return 'Terms of Service: Use this app at your own discretion.'

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5001, debug=True)
