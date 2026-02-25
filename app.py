from flask import Flask
from models import db, User

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_portal.sqlite3'
app.config['SECRET_KEY'] = 'your_secret_key_here'

db.init_app(app)

@app.route('/')
def index():
    return"<h1> Database Configured!</h1><p>Ready to build the Placement Portal.</p>"

if __name__ == '__main__':
    app.run(debug=True)