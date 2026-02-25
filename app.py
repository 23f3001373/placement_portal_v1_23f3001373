from flask import Flask, render_template, request, redirect, url_for, flash 
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Drive, Application

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
        flash('Access denied: Admins only.')
        return redirect(url_for('login'))
     
    total_students = User.query.filter_by(role='student').count()
    total_companies = User.query.filter_by(role='company').count()
    total_drives = Drive.query.count()
    total_applications = Application.query.count()
    
    pending_companies = User.query.filter_by(role='company', is_approved=False).all()
    approved_companies = User.query.filter_by(role='company', is_approved=True).all()
    students = User.query.filter_by(role='student').all()
    
    pending_drives = Drive.query.filter_by(status='Pending').all()
    
    return render_template('admin_dashboard.html', 
                           stats={'students': total_students, 'companies': total_companies, 
                                  'drives': total_drives, 'apps': total_applications},
                           pending_companies=pending_companies,
                           approved_companies=approved_companies,
                           students=students,
                           pending_drives=pending_drives)


@app.route('/approve_drive/<int:drive_id>', methods=['POST'])
@login_required

def approve_drive(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
        
    drive = Drive.query.get_or_404(drive_id)
    drive.status = 'Approved'
    db.session.commit()
    
    flash(f'Placement drive "{drive.job_title}" has been approved!', 'success')
    return redirect(url_for('admin_dashboard'))
 

@app.route('/approve_company/<int:company_id>', methods=['POST'])
@login_required

def approve_company(company_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
        
    company = User.query.get_or_404(company_id)
    company.is_approved = True
    db.session.commit()
    
    flash(f'Company "{company.company_name}" has been approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/company_dashboard')
@login_required

def company_dashboard():
    # Security check: Kick out non-companies
    if current_user.role != 'company':
        flash('Access denied: Companies only.')
        return redirect(url_for('login'))
        
    # Fetch all drives created by this specific company 
    drives = Drive.query.filter_by(company_id=current_user.id).all()
    
    return render_template('company_dashboard.html', drives=drives)

@app.route('/create_drive', methods=['GET', 'POST'])
@login_required

def create_drive():
    if current_user.role != 'company':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        # Get data from the form [cite: 57-60]
        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        eligibility_criteria = request.form.get('eligibility_criteria')
        application_deadline = request.form.get('application_deadline')
        
        # Create the new drive with a default status of 'Pending' Admin approval 
        new_drive = Drive(
            company_id=current_user.id,
            job_title=job_title,
            job_description=job_description,
            eligibility_criteria=eligibility_criteria,
            application_deadline=application_deadline,
            status='Pending' 
        )
        
        db.session.add(new_drive)
        db.session.commit()
        
        flash('Placement drive created successfully! It is currently pending Admin approval.')
        return redirect(url_for('company_dashboard'))
        
    return render_template('create_drive.html')

@app.route('/student_dashboard')
@login_required

def student_dashboard():
    # Security check: Kick out non-students
    if current_user.role != 'student':
        flash('Access denied: Students only.')
        return redirect(url_for('login'))
        
    # Fetch all applications submitted by this student [cite: 41, 118-119]
    my_applications = Application.query.filter_by(student_id=current_user.id).all()
    
    # Extract just the Drive IDs the student has already applied to
    applied_drive_ids = [app.drive_id for app in my_applications]
    
    # Fetch all 'Approved' drives [cite: 39, 118]
    # Filter out the ones the student has already applied to 
    if applied_drive_ids:
        available_drives = Drive.query.filter(Drive.status == 'Approved', Drive.id.notin_(applied_drive_ids)).all()
    else:
        available_drives = Drive.query.filter_by(status='Approved').all()
        
    return render_template('student_dashboard.html', 
                           available_drives=available_drives, 
                           my_applications=my_applications)

@app.route('/apply/<int:drive_id>', methods=['POST'])
@login_required
def apply(drive_id):
    if current_user.role != 'student':
        return redirect(url_for('login'))
        
    # Double-check if the student already applied (backend validation) 
    existing_app = Application.query.filter_by(student_id=current_user.id, drive_id=drive_id).first()
    if existing_app:
        flash('You have already applied for this placement drive.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    # Create the new application [cite: 40, 120]
    new_application = Application(
        student_id=current_user.id, 
        drive_id=drive_id, 
        status='Applied' # Default status
    )
    db.session.add(new_application)
    db.session.commit()
    
    flash('Successfully applied to the placement drive!', 'success')
    return redirect(url_for('student_dashboard'))
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