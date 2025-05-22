# 📌 Project Title
**Securing an Existing Banking Application — Security Assessment and Improvement of a Web-Based Banking Application**

## 👥 Group Members
- Member 1: [Busadre, Christian Siam B.]
- Member 2: [Lagdaan, Jeremy C.]
- Member 3: [Palomares, Juan Paolo C.]

---

## 🧾 Introduction
This project focuses on re-engineering and securing an existing Flask-based banking application. The goal is to identify and remediate security vulnerabilities, strengthen the application’s architecture, and demonstrate secure software development best practices.

## 🎯 Objectives
- Assess the security posture of the original application.
- Fix critical and common security flaws.
- Improve authentication, authorization, session handling, and error reporting.
- Harden data validation, secure data storage, and rate limiting.
- Demonstrate a secure deployment using Flask and MySQL.

---

## 📦 Original Application Features
- **User Authentication:** Login, registration, password recovery
- **Account Management:** View balance, transaction history
- **Fund Transfer:** Transfer between users with confirmation and logging
- **Role Management:** Admin, Manager, Regular Users
- **PSGC Integration:** Location selector for Philippines
- **Admin Panel:** Approve users, deposit funds, update profiles
- **Manager Panel:** Manage admins and monitor all activities

---

## 🧪 Security Assessment Findings
- 🔓 **Weak password policies** (e.g., accepted short/simple passwords)
- ⚠️ **No validation on some form inputs** (transfer/deposit fields)
- ❌ **Session fixation risk** (missing session security settings)
- 🚫 **No output escaping** in some Jinja2 templates (possible XSS)
- 🐛 **Uncaught exceptions and debug info visible**
- 💾 **Float used for balances** (risk of precision loss)
- ⛔ **No timeout or error handling for external PSGC API**

---

## 🔐 Security Improvements Implemented
- 🔑 Strong password validation with regex and min length
- 🔐 Secure password hashing with `bcrypt`
- 🧹 Normalized emails/usernames (trim, lowercase)
- 🧱 Switched from `Float` to `Decimal` for monetary data
- 🧼 CSRF protection enabled via `Flask-WTF`
- 🔒 Rate limiting with `Flask-Limiter` on sensitive routes
- 🧯 Exception handling for PSGC API calls
- 📛 Restricted self-transfers, enforced role-based control
- 🧰 Secure cookie/session settings (`HttpOnly`, `Secure`, `SameSite`)
- 🛡 Output escaping enforced on user-facing templates
- 🧪 Transaction logs improved for auditing
- 🌐 Optional HTTPS enforcement via `Flask-Talisman`

---

## 🧨 Penetration Testing Report
### Vulnerabilities Identified:
- Weak password accepted (e.g., "1234")
- Unauthenticated transfer attempts (forced browsing)
- Exposed error messages (stack traces in debug)
- Session fixation through fixed session cookies

### Exploitation Steps:
- Brute force login with weak password
- Modify HTML to submit transfer to other users
- Trigger unhandled exceptions and view debug info

### Recommendations:
- Enforce stronger password rules
- Sanitize and validate all inputs
- Harden session and CSRF protections
- Disable debug mode and use error templates

---

## 🛠 Remediation Plan
| Issue | Fix |
|------|-----|
| Weak Passwords | Enforced strong regex and min length in forms |
| Float for Money | Changed to `Decimal` with `Numeric(12, 2)` |
| CSRF Missing | Initialized `CSRFProtect` globally in `app.py` |
| Session Fixation | Enabled `session_protection = 'strong'` |
| Output Encoding | Avoided using `|safe`, used `|e` and defaults |
| Debug Info | Added 404/500 handlers and disabled debug in production |
| Rate Abuse | Added `Flask-Limiter` with tiered throttling per role |

---

## 🧱 Technology Stack
- **Backend:** Python 3.9, Flask
- **Database:** MySQL with SQLAlchemy ORM
- **Frontend:** HTML, CSS, Bootstrap 5
- **Authentication:** Flask-Login, Flask-Bcrypt, Flask-WTF
- **Security Libraries:** Flask-Limiter, Flask-Talisman (optional), Flask-WTF
- **Geographic API:** PSGC API (with caching and fallback)

---

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.7+
- pip
- MySQL Server (or MariaDB)

### Local Setup
```bash
git clone https://github.com/yourusername/simple-banking-app-v2.git
cd simple-banking-app-v2
pip install -r requirements.txt
cp .env.example .env  # Fill in your credentials
python init_db.py
python app.py
```

### Environment Variables Example:
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

### Deploy to PythonAnywhere
- Upload via Git
- Configure manual web app (Python 3.8+)
- Set environment variables in dashboard
- Run `python init_db.py` to initialize DB
- Ensure `.env` file is secure and excluded in `.gitignore`

---

This project was completed as part of a platform security course to demonstrate secure software development, vulnerability assessment, and remediation best practices.