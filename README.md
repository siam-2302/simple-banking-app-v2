# Project Title
Securing an Existing Banking Application – Security Assessment and Improvement of a Web-Based Banking Application

## Group Members
- Member 1 – Role
- Member 2 – Role
- Member 3 – Role
- Member 4 – Role

## Introduction
This project aims to assess and improve the security posture of an existing open-source banking web application. The application simulates real-world banking functionality including user account management, fund transfers, and role-based user permissions. Our team performed a comprehensive security review and applied best practices to secure the system against common web vulnerabilities.

## Objectives
- Identify and document security vulnerabilities in the original application
- Implement robust security measures while preserving core banking functionality
- Apply secure coding principles and OWASP Top 10 practices
- Demonstrate the effectiveness of improvements through penetration testing

## Original Application Features
- User authentication (registration, login, password reset)
- Account management (view balance, transaction history)
- Fund transfers between users
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

## Security Improvements Implemented
- Password validation improved: min 8 characters, special char, number, uppercase
- Decimal precision (`Numeric`) replaced float for all monetary values
- Proper CSRF protection added to all forms using Flask-WTF
- Rate limiting enforced on login, registration, and admin actions using Flask-Limiter
- PSGC API hardened with timeout and error handling
- Session configuration secured (HttpOnly, Secure, SameSite)
- Output encoding via Jinja2 to prevent reflected XSS
- Bcrypt used for password hashing
- Flask-Talisman suggested for HTTPS enforcement

## Penetration Testing Report
- **SQL Injection:** Prevented by SQLAlchemy ORM
- **CSRF Attacks:** Fixed via CSRF token validation
- **Brute Force Login:** Rate limiting successfully blocked repeated attempts
- **XSS:** Manual tests confirmed escaped user-generated content
- **Broken Authentication:** Password reset tokens now expire securely

## Remediation Plan
1. Enforce strong password policies (done)
2. Sanitize and validate all form inputs (done)
3. Escape all rendered output from users (done)
4. Introduce HTTPS and secure headers (recommended for deployment)
5. Update all dependencies and monitor via `pip-audit` (suggested)

## Technology Stack
- **Backend:** Python, Flask, SQLAlchemy
- **Frontend:** HTML5, CSS3, Bootstrap 5
- **Database:** MySQL or MariaDB with `Decimal`-based financial fields
- **Security:** Flask-Bcrypt, Flask-WTF, Flask-Limiter, Flask-Login, Flask-Talisman
- **API:** PSGC GitLab API for hierarchical location selection

## Setup Instructions

### Prerequisites
- Python 3.7+
- pip
- MySQL Server 5.7+ or MariaDB 10.2+

### Installation
```bash
git clone https://github.com/yourusername/simple-banking-app-v2.git
cd simple-banking-app-v2
pip install -r requirements.txt
cp .env.example .env  # Configure DB credentials
python init_db.py
python app.py
```
Access the app at: `http://localhost:5000`

### Sample .env Configuration
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
- Push code to GitHub and clone into PythonAnywhere
- Set up virtualenv and install requirements
- Configure `.env` variables
- Set WSGI file path and run `init_db.py`

## License
MIT License — see `LICENSE` file

---
**Project for academic use only. Not for real-world financial deployment.**
