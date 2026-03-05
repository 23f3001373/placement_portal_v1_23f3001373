# Placement Portal Application

A web-based Placement Portal that allows **Admin**, **Company**, and **Student** users to interact with the campus recruitment system based on their roles.

Built with **Flask**, **Jinja2**, **SQLite**, and **Bootstrap 5**.

---

## Features

### Admin
- Pre-existing superuser account
- Approve or reject company registrations
- Approve or reject placement drives
- View and manage all students, companies, and placement drives
- Edit, delete, or blacklist students and companies
- Search by name, ID, industry, or contact info
- View complete historical placement data

### Company
- Register and create a company profile (pending admin approval)
- Create, edit, close, or delete placement drives
- View student applications for their drives
- Shortlist students and update application status (Applied → Shortlisted → Selected / Rejected)
- Edit company profile (name, HR contact, website, industry)

### Student
- Self-register, login, and update profile
- Upload resume (PDF/DOC)
- View approved placement drives with search functionality
- Apply to placement drives (duplicate prevention enforced)
- View application status and placement history

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask (Python) |
| Frontend | Jinja2, HTML, CSS, Bootstrap 5 |
| Database | SQLite |
| Auth | Flask-Login, Werkzeug (password hashing) |

---

## Project Setup

### Prerequisites
- **Python 3.8+**
- **pip**

### Step 1: Create a Virtual Environment

Open a terminal in the project folder and run:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the beginning of your terminal prompt after activation.

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, Flask-SQLAlchemy, Flask-Login, and Werkzeug.

### Step 3: Run the Application

```bash
python app.py
```

This will:
1. Automatically create the SQLite database (`instance/placement_portal.sqlite3`)
2. Create the default admin user if it doesn't exist
3. Start the Flask development server

### Step 4: Open in Browser

Navigate to: **http://127.0.0.1:5000**

### Default Admin Credentials

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

---

## Project Structure

```
placement_portal/
├── app.py                  # Main Flask application with all routes
├── models.py               # SQLAlchemy database models (User, Drive, Application)
├── create_admin.py         # Standalone script to create admin user
├── requirements.txt        # Python dependencies
├── README.md               
├── instance/
│   └── placement_portal.sqlite3   # SQLite database (auto-generated)
├── static/
│   └── resumes/            # Uploaded student resumes
└── templates/
    ├── base.html               # Base template with Bootstrap & flash messages
    ├── login.html              # Login page
    ├── register.html           # Registration form (Student / Company)
    ├── admin_dashboard.html    # Admin dashboard with stats & management
    ├── admin_edit_user.html    # Admin edit user details
    ├── admin_history.html      # Historical placement data
    ├── company_dashboard.html  # Company dashboard with drives
    ├── create_drive.html       # Create new placement drive
    ├── edit_drive.html         # Edit existing drive
    ├── drive_applications.html # View applications for a drive
    ├── edit_company_profile.html # Company profile editing
    ├── edit_profile.html       # Student profile editing
    └── student_dashboard.html  # Student dashboard with drives & history
```

---

## Database Schema

### User
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Unique user ID |
| username | String | Login username |
| password | String | Hashed password |
| role | String | `admin` / `company` / `student` |
| name | String | Student full name |
| department | String | Student department |
| resume_filename | String | Uploaded resume file name |
| company_name | String | Company name |
| hr_contact | String | HR contact details |
| website | String | Company website URL |
| industry | String | Company industry |
| is_approved | Boolean | Company approval status |
| is_blacklisted | Boolean | Blacklist status |

### Drive
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Drive ID |
| company_id | Integer (FK) | References User.id |
| job_title | String | Position title |
| job_description | Text | Full job description |
| eligibility_criteria | Text | Who can apply |
| application_deadline | String | Deadline date |
| status | String | `Pending` / `Approved` / `Rejected` / `Closed` |

### Application
| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Application ID |
| student_id | Integer (FK) | References User.id |
| drive_id | Integer (FK) | References Drive.id |
| application_date | DateTime | When applied |
| status | String | `Applied` / `Shortlisted` / `Selected` / `Rejected` |

---

## Frameworks & Libraries Used

- **Flask** – Web framework
- **Flask-SQLAlchemy** – ORM for SQLite database
- **Flask-Login** – User session management & authentication
- **Werkzeug** – Password hashing & file upload security
- **Jinja2** – HTML templating engine (built into Flask)
- **Bootstrap 5** – Responsive UI framework (via CDN)
