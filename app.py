from flask import Flask, render_template, request, redirect, url_for, flash 
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_portal.sqlite3'
app.config['SECRET_KEY'] = 'your_secret_key_here'

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Check if it's a company and if they are approved 
            if user.role == 'company' and not user.is_approved:
                flash('Your company account is pending Admin approval.')
                return redirect(url_for('login'))
                
            login_user(user)
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'company':
                return redirect(url_for('company_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password. Please try again.')
            
    return render_template('login.html')
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    return "<h1>Welcome Admin!</h1><a href='/logout'>Logout</a>"

@app.route('/company_dashboard')
@login_required
def company_dashboard():
    if current_user.role != 'company':
        return "Unauthorized", 403
    return "<h1>Welcome Company!</h1><a href='/logout'>Logout</a>"


@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return "unauthorized", 403
    return "<h1>Welcome Student!</h1><a href='logout'>Logout</a>"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role') 
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        
        if role == 'student':
            name = request.form.get('name')
            department = request.form.get('department')
            new_user = User(username=username, password=hashed_pw, role=role, name=name, department=department)
            
        elif role == 'company':
            company_name = request.form.get('company_name')
            hr_contact = request.form.get('hr_contact')
            new_user = User(username=username, password=hashed_pw, role=role, company_name=company_name, hr_contact=hr_contact)
            
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)