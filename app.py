import os
from flask import Flask, render_template, request, redirect, url_for, flash 
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Drive, Application
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_portal.sqlite3'
app.config['SECRET_KEY'] = 'super_secret_key_change_this_later' 

app.config['UPLOAD_FOLDER'] = 'static/resumes'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Max upload size: 2MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# Programmatic DB creation (required by project spec)
with app.app_context():
    db.create_all()

    # Auto-create admin if not exists
    existing_admin = User.query.filter_by(role='admin').first()
    if not existing_admin:
        hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
        admin_user = User(username='admin', password=hashed_pw, role='admin')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created (Username: admin, Password: admin123)")

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            if user.is_blacklisted:
                flash('Your account has been blacklisted by the Administrator.', 'danger')
                return redirect(url_for('login'))
            if user.role == 'company' and not user.is_approved:
                flash('Your company account is pending Admin approval.', 'warning')
                return redirect(url_for('login'))
                
            login_user(user)
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'company':
                return redirect(url_for('company_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role') 
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        
        if role == 'student':
            name = request.form.get('name')
            department = request.form.get('department')
            new_user = User(username=username, password=hashed_pw, role=role, 
                          name=name, department=department)
            
        elif role == 'company':
            company_name = request.form.get('company_name')
            hr_contact = request.form.get('hr_contact')
            website = request.form.get('website')
            industry = request.form.get('industry')
            new_user = User(username=username, password=hashed_pw, role=role, 
                          company_name=company_name, hr_contact=hr_contact,
                          website=website, industry=industry)
        else:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('register'))
            
        db.session.add(new_user)
        db.session.commit()
        
        if role == 'company':
            flash('Registration successful! Your account is pending Admin approval.', 'success')
        else:
            flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')


# ─────────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────────

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('login'))
    
    # Calculate statistics
    total_students = User.query.filter_by(role='student').count()
    total_companies = User.query.filter_by(role='company').count()
    total_drives = Drive.query.count()
    total_applications = Application.query.count()
    
    # Fetch pending approvals
    pending_companies = User.query.filter_by(role='company', is_approved=False).all()
    pending_drives = Drive.query.filter_by(status='Pending').all()
    
    # Search functionality
    search_query = request.args.get('search', '')
    
    if search_query:
        if search_query.isdigit():
            approved_companies = User.query.filter_by(role='company', is_approved=True, id=int(search_query)).all()
            students = User.query.filter_by(role='student', id=int(search_query)).all()
        else:
            # Companies: search by Name, Industry, or HR Contact
            approved_companies = User.query.filter(
                User.role == 'company', 
                User.is_approved == True, 
                db.or_(
                    User.company_name.ilike(f'%{search_query}%'),
                    User.industry.ilike(f'%{search_query}%'),
                    User.hr_contact.ilike(f'%{search_query}%')
                )
            ).all()
            
            # Students: search by Name, Username (contact info)
            students = User.query.filter(
                User.role == 'student', 
                db.or_(
                    User.name.ilike(f'%{search_query}%'),
                    User.username.ilike(f'%{search_query}%')
                )
            ).all()
    else:
        approved_companies = User.query.filter_by(role='company', is_approved=True).all()
        students = User.query.filter_by(role='student').all()
    
    return render_template('admin_dashboard.html', 
                           stats={'students': total_students, 'companies': total_companies, 
                                  'drives': total_drives, 'apps': total_applications},
                           pending_companies=pending_companies,
                           approved_companies=approved_companies,
                           students=students,
                           pending_drives=pending_drives,
                           search_query=search_query)


@app.route('/admin/history')
@login_required
def admin_history():
    if current_user.role != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('login'))
    
    all_drives = Drive.query.order_by(Drive.id.desc()).all()
    all_applications = Application.query.order_by(Application.application_date.desc()).all()
    
    return render_template('admin_history.html', drives=all_drives, applications=all_applications)


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


@app.route('/reject_company/<int:company_id>', methods=['POST'])
@login_required
def reject_company(company_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
        
    company = User.query.get_or_404(company_id)
    company_name = company.company_name
    db.session.delete(company)
    db.session.commit()
    
    flash(f'Company "{company_name}" has been rejected and removed.', 'warning')
    return redirect(url_for('admin_dashboard'))


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


@app.route('/reject_drive/<int:drive_id>', methods=['POST'])
@login_required
def reject_drive(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
        
    drive = Drive.query.get_or_404(drive_id)
    drive.status = 'Rejected'
    db.session.commit()
    
    flash(f'Placement drive "{drive.job_title}" has been rejected.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/blacklist/<int:user_id>', methods=['POST'])
@login_required
def toggle_blacklist(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    user.is_blacklisted = not user.is_blacklisted
    db.session.commit()
    
    status = "blacklisted" if user.is_blacklisted else "un-blacklisted"
    flash(f'User {user.username} has been {status}.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    
    # Cascade delete: remove all related data to prevent foreign key errors
    if user.role == 'company':
        # Delete all applications for drives owned by this company
        company_drives = Drive.query.filter_by(company_id=user.id).all()
        for drive in company_drives:
            Application.query.filter_by(drive_id=drive.id).delete()
        # Delete all drives owned by this company
        Drive.query.filter_by(company_id=user.id).delete()
    elif user.role == 'student':
        # Delete all applications by this student
        Application.query.filter_by(student_id=user.id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        if user.role == 'student':
            user.name = request.form.get('name')
            user.department = request.form.get('department')
        elif user.role == 'company':
            user.company_name = request.form.get('company_name')
            user.hr_contact = request.form.get('hr_contact')
            user.website = request.form.get('website')
            user.industry = request.form.get('industry')
            
        db.session.commit()
        flash('User details updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('admin_edit_user.html', user=user)


# ─────────────────────────────────────────────
# COMPANY ROUTES
# ─────────────────────────────────────────────

@app.route('/company_dashboard')
@login_required
def company_dashboard():
    if current_user.role != 'company':
        flash('Access denied: Companies only.', 'danger')
        return redirect(url_for('login'))
        
    drives = Drive.query.filter_by(company_id=current_user.id).all()
    
    return render_template('company_dashboard.html', drives=drives)


@app.route('/edit_company_profile', methods=['GET', 'POST'])
@login_required
def edit_company_profile():
    if current_user.role != 'company':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        current_user.company_name = request.form.get('company_name')
        current_user.hr_contact = request.form.get('hr_contact')
        current_user.website = request.form.get('website')
        current_user.industry = request.form.get('industry')
        
        db.session.commit()
        flash('Company profile updated successfully!', 'success')
        return redirect(url_for('company_dashboard'))
        
    return render_template('edit_company_profile.html')


@app.route('/create_drive', methods=['GET', 'POST'])
@login_required
def create_drive():
    if current_user.role != 'company':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        eligibility_criteria = request.form.get('eligibility_criteria')
        application_deadline = request.form.get('application_deadline')
        
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
        
        flash('Placement drive created successfully! It is currently pending Admin approval.', 'success')
        return redirect(url_for('company_dashboard'))
        
    return render_template('create_drive.html')


@app.route('/edit_drive/<int:drive_id>', methods=['GET', 'POST'])
@login_required
def edit_drive(drive_id):
    if current_user.role != 'company':
        return redirect(url_for('login'))
        
    drive = Drive.query.get_or_404(drive_id)
    
    if drive.company_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('company_dashboard'))
        
    if request.method == 'POST':
        drive.job_title = request.form.get('job_title')
        drive.job_description = request.form.get('job_description')
        drive.eligibility_criteria = request.form.get('eligibility_criteria')
        drive.application_deadline = request.form.get('application_deadline')
        
        db.session.commit()
        flash('Drive updated successfully!', 'success')
        return redirect(url_for('company_dashboard'))
        
    return render_template('edit_drive.html', drive=drive)


@app.route('/close_drive/<int:drive_id>', methods=['POST'])
@login_required
def close_drive(drive_id):
    if current_user.role != 'company':
        return redirect(url_for('login'))
        
    drive = Drive.query.get_or_404(drive_id)
    if drive.company_id == current_user.id:
        drive.status = 'Closed'
        db.session.commit()
        flash(f'Drive "{drive.job_title}" is now closed.', 'warning')
        
    return redirect(url_for('company_dashboard'))


@app.route('/delete_drive/<int:drive_id>', methods=['POST'])
@login_required
def delete_drive(drive_id):
    if current_user.role != 'company':
        return redirect(url_for('login'))
        
    drive = Drive.query.get_or_404(drive_id)
    if drive.company_id == current_user.id:
        Application.query.filter_by(drive_id=drive_id).delete()
        db.session.delete(drive)
        db.session.commit()
        flash('Placement drive deleted successfully.', 'success')
        
    return redirect(url_for('company_dashboard'))


@app.route('/drive/<int:drive_id>/applications')
@login_required
def drive_applications(drive_id):
    if current_user.role != 'company':
        return redirect(url_for('login'))
        
    drive = Drive.query.get_or_404(drive_id)
    
    if drive.company_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('company_dashboard'))
        
    applications = Application.query.filter_by(drive_id=drive_id).all()
    
    return render_template('drive_applications.html', drive=drive, applications=applications)


@app.route('/update_application/<int:app_id>', methods=['POST'])
@login_required
def update_application(app_id):
    if current_user.role != 'company':
        return redirect(url_for('login'))
        
    application = Application.query.get_or_404(app_id)
    
    if application.drive.company_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('company_dashboard'))
        
    new_status = request.form.get('status')
    if new_status in ['Applied', 'Shortlisted', 'Selected', 'Rejected']:
        application.status = new_status
        db.session.commit()
        flash(f'Application status updated to {new_status}!', 'success')
        
    return redirect(url_for('drive_applications', drive_id=application.drive_id))


# ─────────────────────────────────────────────
# STUDENT ROUTES
# ─────────────────────────────────────────────

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied: Students only.', 'danger')
        return redirect(url_for('login'))
        
    my_applications = Application.query.filter_by(student_id=current_user.id).all()
    applied_drive_ids = [app.drive_id for app in my_applications]
    
    search_query = request.args.get('search', '')
    
    # Only show Approved drives
    query = Drive.query.filter(Drive.status == 'Approved')
    
    # Exclude drives the student already applied to
    if applied_drive_ids:
        query = query.filter(Drive.id.notin_(applied_drive_ids))
        
    # Apply search filter
    if search_query:
        query = query.join(User).filter(
            db.or_(
                Drive.job_title.ilike(f'%{search_query}%'),
                User.company_name.ilike(f'%{search_query}%'),
                Drive.eligibility_criteria.ilike(f'%{search_query}%')
            )
        )
        
    available_drives = query.all()
        
    return render_template('student_dashboard.html', 
                           available_drives=available_drives, 
                           my_applications=my_applications,
                           search_query=search_query)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if current_user.role != 'student':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.department = request.form.get('department')
        
        resume = request.files.get('resume')
        if resume and resume.filename != '':
            filename = secure_filename(resume.filename)
            unique_filename = f"student_{current_user.id}_{filename}"
            resume.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            current_user.resume_filename = unique_filename
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student_dashboard'))
        
    return render_template('edit_profile.html')


@app.route('/apply/<int:drive_id>', methods=['POST'])
@login_required
def apply(drive_id):
    if current_user.role != 'student':
        return redirect(url_for('login'))
    
    # Check if student is blacklisted
    if current_user.is_blacklisted:
        flash('Your account has been blacklisted. You cannot apply to drives.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    # Check if drive is approved (prevent applying to closed/rejected drives)
    drive = Drive.query.get_or_404(drive_id)
    if drive.status != 'Approved':
        flash('This placement drive is not currently accepting applications.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    # Prevent duplicate applications
    existing_app = Application.query.filter_by(student_id=current_user.id, drive_id=drive_id).first()
    if existing_app:
        flash('You have already applied for this placement drive.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    new_application = Application(
        student_id=current_user.id, 
        drive_id=drive_id, 
        status='Applied'
    )
    db.session.add(new_application)
    db.session.commit()
    
    flash('Successfully applied to the placement drive!', 'success')
    return redirect(url_for('student_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)