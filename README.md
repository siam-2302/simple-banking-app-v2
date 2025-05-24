# Project Title
Securing an Existing Banking Application – Security Assessment and Improvement of a Web-Based Banking Application

## Group Members
- Member 1: [Busadre, Christian Siam B.]
- Member 2: [Lagdaan, Jeremy C.]
- Member 3: [Palomares, Juan Paolo C.]

## Introduction
This project aims to assess and improve the security posture of an existing open-source banking web application. The application simulates real-world banking functionality including user account management, fund transfers, and role-based user permissions. Our team performed a comprehensive security review, refactored the user interface, and applied secure coding practices to harden the system against common web threats.

The original application was cloned from:  
[https://github.com/lanlanjr/simple-banking-app](https://github.com/lanlanjr/simple-banking-app)

The repository was cloned and edited on Visual Studio Code and later uploaded on GitHub

## Objectives
- Identify and document security vulnerabilities in the original application
- Implement robust security measures while preserving core banking functionality
- Apply secure coding principles and OWASP Top 10 practices
- Enhance usability and consistency through UI redesign
- Demonstrate the effectiveness of improvements through penetration testing

## Original Application Features
- User authentication (registration, login, password reset)
- Account management (view balance, transaction history)
- Fund transfers between users (username/account number based)
- Role-based user management: regular user, admin, manager
- Philippine address data integration using PSGC API

## Security Assessment Findings
- Passwords stored with minimal validation and weak default credentials
- Float values used for balance calculations (risk of rounding errors)
- Lack of error handling for PSGC API failures
- No output escaping on user-generated content (potential XSS)
- No rate limiting on sensitive endpoints (e.g., login)
- No HTTPS enforcement or security headers
- Incomplete session management and CSRF token inconsistencies
- Outdated third-party packages
- Admin/manager actions untracked; audit trail missing

## Security Improvements Implemented
- Password validation: Enforced min length, mixed characters, numbers, uppercase
- Float replaced with `Decimal` for precise financial computation
- CSRF protection standardized across all forms using Flask-WTF
- Rate limiting enforced on key routes using Flask-Limiter
- PSGC API responses handled gracefully with timeout/error fallback
- Secure session settings (Secure, HttpOnly, SameSite)
- Jinja2 autoescaping and strict output sanitization
- Bcrypt for secure password storage
- Flask-Talisman enabled for security headers and HTTPS recommendation
- Activity logging of admin/manager transactions and edits

## Penetration Testing Report
- **SQL Injection:** Mitigated via SQLAlchemy ORM usage
- **CSRF Attacks:** All routes protected by valid CSRF tokens
- **Brute Force Login:** Thwarted via rate limiting policies
- **XSS:** Escaped user-generated input on all dynamic templates
- **Broken Authentication:** Reset tokens expire securely; no token reuse

## Remediation Plan
1. Strengthen input validation on all user-facing forms ✅
2. Replace insecure float calculations with `Decimal` precision ✅
3. Escape dynamic content and form messages in templates ✅
4. Enable secure headers and HTTPS enforcement via Flask-Talisman ✅
5. Maintain up-to-date dependencies via `pip-audit` or GitHub Dependabot ✅
6. Create audit trails for privileged operations ✅

## Technology Stack
- **Backend:** Python 3, Flask, SQLAlchemy ORM
- **Frontend:** HTML5, CSS3, Bootstrap 5, Jinja2 Templates
- **Database:** MySQL or MariaDB (Decimal fields for financial data)
- **Security Libraries:** Flask-Bcrypt, Flask-WTF, Flask-Limiter, Flask-Talisman, Flask-Login
- **External API:** PSGC GitLab API for address hierarchy

## Setup Instructions

### Prerequisites
- Python 3.7+
- pip
- MySQL Server 5.7+ or MariaDB 10.2+
- XAMPP (if not familiar with Mysql software)

### Installation
```bash
git clone https://github.com/yourusername/simple-banking-app-v2.git
cd simple-banking-app-v2
pip install -r requirements.txt
python init_db.py(you need to create and copy the contents of .env before running this code)
python app.py
```
### .env Configuration(Create .env file)
```
DATABASE_URL=mysql+pymysql://bankapp:your_password@localhost/simple_banking
MYSQL_USER=bankapp
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=simple_banking
SECRET_KEY=your_secret_key
REDIS_URL=memory://
```



## Deployment (PythonAnywhere)
- Push code to GitHub
- Clone into PythonAnywhere
- Configure a virtualenv and install requirements
- Set environmental variables in the dashboard
- Configure WSGI path and initialize the DB via `init_db.py`

-link: https://hyun23.pythonanywhere.com/login

---
**Project is for academic use only. Not for real-world financial deployment.**
