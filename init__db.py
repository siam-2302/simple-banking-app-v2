import os
import pymysql
from dotenv import load_dotenv
import traceback
import datetime
from werkzeug.security import generate_password_hash

# Load environment variables
load_dotenv()

def init_mysql_database():
    """Initialize the MySQL database directly in Python instead of using schema.sql."""
    mysql_user = os.environ.get('MYSQL_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD')
    mysql_host = os.environ.get('MYSQL_HOST')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_database = os.environ.get('MYSQL_DATABASE')

    try:
        print("Connecting to MySQL server...")
        connection = pymysql.connect(
            host=mysql_host,
            port=int(mysql_port),
            user=mysql_user,
            password=mysql_password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )

        print("Connected to MySQL server.")
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {mysql_database}")
            cursor.execute(f"CREATE DATABASE {mysql_database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {mysql_database}")

            print("Creating tables...")
            cursor.execute("""
                CREATE TABLE user (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(64) NOT NULL UNIQUE,
                    email VARCHAR(120) NOT NULL UNIQUE,
                    firstname VARCHAR(64),
                    lastname VARCHAR(64),
                    address_line VARCHAR(256),
                    region_code VARCHAR(20),
                    region_name VARCHAR(100),
                    province_code VARCHAR(20),
                    province_name VARCHAR(100),
                    city_code VARCHAR(20),
                    city_name VARCHAR(100),
                    barangay_code VARCHAR(20),
                    barangay_name VARCHAR(100),
                    postal_code VARCHAR(10),
                    phone VARCHAR(20),
                    password_hash VARCHAR(128) NOT NULL,
                    account_number VARCHAR(10) NOT NULL UNIQUE,
                    balance FLOAT DEFAULT 1000.0,
                    status VARCHAR(20) DEFAULT 'pending',
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_manager BOOLEAN DEFAULT FALSE,
                    date_registered DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_username (username),
                    INDEX idx_email (email),
                    INDEX idx_account_number (account_number)
                ) ENGINE=InnoDB;
            """)

            cursor.execute("""
                CREATE TABLE transaction (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    sender_id INT,
                    receiver_id INT,
                    amount FLOAT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    transaction_type VARCHAR(20) DEFAULT 'transfer',
                    details TEXT,
                    FOREIGN KEY (sender_id) REFERENCES user (id),
                    FOREIGN KEY (receiver_id) REFERENCES user (id),
                    INDEX idx_sender (sender_id),
                    INDEX idx_receiver (receiver_id),
                    INDEX idx_timestamp (timestamp)
                ) ENGINE=InnoDB;
            """)

            connection.commit()
            print("Database schema created successfully.")

    except Exception as e:
        print(f"Error during database initialization: {e}")
        print(traceback.format_exc())
        return False

    finally:
        if 'connection' in locals() and connection.open:
            connection.close()
            print("MySQL connection closed.")

    return True

def init_flask_app_db():
    """Initialize SQLAlchemy-based Flask app tables and sample data."""
    try:
        from app import app
        from extensions import db
        from models import User, Transaction

        with app.app_context():
            db.drop_all()
            db.create_all()

            # Create users
            def create_user_if_not_exists(**kwargs):
                if not User.query.filter_by(username=kwargs['username']).first():
                    user = User(**kwargs)
                    user.set_password(kwargs.get("password"))
                    db.session.add(user)
                    db.session.commit()
                    print(f"Created user '{user.username}'")

            create_user_if_not_exists(
                username="manager",
                email="manager@bankapp.com",
                account_number="0000000000",
                status="active",
                is_admin=True,
                is_manager=True,
                balance=1000.0,
                firstname="System",
                lastname="Manager",
                address_line="123 Taft Avenue",
                region_code="130000000",
                region_name="National Capital Region",
                province_code="137400000",
                province_name="NCR Fourth District",
                city_code="137404000",
                city_name="Manila",
                barangay_code="137404022",
                barangay_name="Malate",
                postal_code="1004",
                phone="+63917123456",
                password="Manager123!"
            )

            create_user_if_not_exists(
                username="admin",
                email="admin@bankapp.com",
                account_number="0000000001",
                status="active",
                is_admin=True,
                is_manager=False,
                balance=1000.0,
                firstname="Admin",
                lastname="User",
                address_line="456 Osmeña Boulevard",
                region_code="070000000",
                region_name="Central Visayas",
                province_code="072200000",
                province_name="Cebu",
                city_code="072217000",
                city_name="Cebu City",
                barangay_code="072217009",
                barangay_name="Guadalupe",
                postal_code="6000",
                phone="+63918765432",
                password="Admin123!"
            )

            create_user_if_not_exists(
                username="testuser",
                email="test@example.com",
                account_number="1234567890",
                status="active",
                balance=1000.0,
                firstname="Test",
                lastname="User",
                address_line="789 Quimpo Boulevard",
                region_code="110000000",
                region_name="Davao Region",
                province_code="112400000",
                province_name="Davao del Sur",
                city_code="112402000",
                city_name="Davao City",
                barangay_code="112402036",
                barangay_name="Matina Crossing",
                postal_code="8000",
                phone="+63929876543",
                password="Test123!"
            )

            print("Flask database initialized with admin, manager, and test users.")
            return True

    except Exception as e:
        print(f"Error initializing Flask app DB: {e}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("== Initializing Simple Banking App Database ==")
    if init_mysql_database():
        if init_flask_app_db():
            print("Database initialization complete.")
        else:
            print("Flask app database setup failed.")
            exit(1)
    else:
        print("MySQL schema setup failed.")
        exit(1)
