from extensions import db, bcrypt
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import random
import string
from decimal import Decimal
from sqlalchemy import Numeric

# Transaction types as constants
TRANSFER = 'transfer'
DEPOSIT = 'deposit'
USER_EDIT = 'user_edit'


def generate_account_number():
    """Generate a random 10-digit account number"""
    return ''.join(random.choices(string.digits, k=10))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    firstname = db.Column(db.String(64), nullable=True)
    lastname = db.Column(db.String(64), nullable=True)
    address_line = db.Column(db.String(256), nullable=True)
    region_code = db.Column(db.String(20), nullable=True)
    region_name = db.Column(db.String(100), nullable=True)
    province_code = db.Column(db.String(20), nullable=True)
    province_name = db.Column(db.String(100), nullable=True)
    city_code = db.Column(db.String(20), nullable=True)
    city_name = db.Column(db.String(100), nullable=True)
    barangay_code = db.Column(db.String(20), nullable=True)
    barangay_name = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(128))
    account_number = db.Column(db.String(10), unique=True, default=generate_account_number)
    balance = db.Column(Numeric(12, 2), default=Decimal('1000.00'))
    status = db.Column(db.String(20), default='pending')
    is_admin = db.Column(db.Boolean, default=False)
    is_manager = db.Column(db.Boolean, default=False)
    date_registered = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    transactions_sent = db.relationship('Transaction', foreign_keys='Transaction.sender_id', backref='sender', lazy='dynamic')
    transactions_received = db.relationship('Transaction', foreign_keys='Transaction.receiver_id', backref='receiver', lazy='dynamic')

    @property
    def full_address(self):
        address_parts = []
        if self.address_line:
            address_parts.append(self.address_line)
        if self.barangay_name:
            address_parts.append(f"Barangay {self.barangay_name}")
        if self.city_name:
            address_parts.append(self.city_name)
        if self.province_name:
            address_parts.append(self.province_name)
        if self.region_name:
            address_parts.append(self.region_name)
        if self.postal_code:
            address_parts.append(self.postal_code)

        return ", ".join(address_parts) if address_parts else "No address provided"

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.status == 'active'

    def transfer_money(self, recipient, amount):
        amount = Decimal(amount)
        if self.balance >= amount and amount > 0 and self.id != recipient.id and (self.status == 'active' or self.is_admin or self.is_manager):
            self.balance -= amount
            recipient.balance += amount
            transaction = Transaction(
                sender_id=self.id,
                receiver_id=recipient.id,
                amount=amount,
                transaction_type=TRANSFER,
                timestamp=datetime.datetime.utcnow(),
                details=f"Transfer of {amount} from {self.username} to {recipient.username}"
            )
            db.session.add(transaction)
            return True
        return False

    def deposit(self, amount, admin_user):
        amount = Decimal(amount)
        if amount <= 0:
            return False
        self.balance += amount
        transaction = Transaction(
            sender_id=admin_user.id,
            receiver_id=self.id,
            amount=amount,
            transaction_type=DEPOSIT,
            timestamp=datetime.datetime.utcnow(),
            details=f"Deposit of {amount} by {admin_user.username}"
        )
        db.session.add(transaction)
        return True

    def get_recent_transactions(self, limit=10):
        sent = self.transactions_sent.filter(Transaction.transaction_type != USER_EDIT).order_by(Transaction.timestamp.desc()).limit(limit).all()
        received = self.transactions_received.filter(Transaction.transaction_type != USER_EDIT).order_by(Transaction.timestamp.desc()).limit(limit).all()
        all_transactions = sorted(sent + received, key=lambda x: x.timestamp, reverse=True)
        return all_transactions[:limit]

    def activate_account(self):
        self.status = 'active'
        db.session.commit()

    def deactivate_account(self):
        self.status = 'deactivated'
        db.session.commit()

    def is_account_manager(self):
        return self.is_manager

    def can_manage_user(self, user):
        if self.is_manager:
            return not user.is_manager
        if self.is_admin:
            return not user.is_admin and not user.is_manager
        return False


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(Numeric(12, 2))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    transaction_type = db.Column(db.String(20), default=TRANSFER)
    details = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Transaction {self.id} - {self.amount}>'
