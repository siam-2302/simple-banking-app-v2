from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, RadioField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange, Optional, Length, Regexp
from models import User

# Password strength policy
strong_password = [
    DataRequired(),
    Length(min=8, message='Password must be at least 8 characters long'),
    Regexp(r'^(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).+$',
           message='Password must include at least one uppercase letter, one digit, and one special character')
]

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=strong_password)
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        username.data = username.data.strip()
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        email.data = email.data.strip().lower()
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class TransferForm(FlaskForm):
    transfer_type = RadioField('Transfer Type', 
                              choices=[('username', 'By Username'), ('account', 'By Account Number')],
                              default='username')
    recipient_username = StringField('Recipient Username', validators=[Optional()])
    recipient_account = StringField('Recipient Account Number', validators=[Optional()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0")])
    submit = SubmitField('Transfer')

    def validate(self, extra_validators=None):
        if not super(TransferForm, self).validate():
            return False

        if self.transfer_type.data == 'username' and not self.recipient_username.data:
            self.recipient_username.errors = ['Username is required when transferring by username']
            return False

        if self.transfer_type.data == 'account' and not self.recipient_account.data:
            self.recipient_account.errors = ['Account number is required when transferring by account number']
            return False

        if not self.recipient_username.data and not self.recipient_account.data:
            self.recipient_username.errors = ['Either username or account number must be provided']
            return False

        user = None
        if self.transfer_type.data == 'username' and self.recipient_username.data:
            user = User.query.filter_by(username=self.recipient_username.data).first()
            if not user:
                self.recipient_username.errors = ['No user with that username']
                return False
        elif self.transfer_type.data == 'account' and self.recipient_account.data:
            user = User.query.filter_by(account_number=self.recipient_account.data).first()
            if not user:
                self.recipient_account.errors = ['No account with that number']
                return False

        return True

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=strong_password)
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class DepositForm(FlaskForm):
    account_number = StringField('Account Number', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0")])
    submit = SubmitField('Deposit')

    def validate(self, extra_validators=None):
        if not super(DepositForm, self).validate():
            return False

        user = User.query.filter_by(account_number=self.account_number.data).first()
        if not user:
            self.account_number.errors = ['No account with that number']
            return False

        return True

class UserEditForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    firstname = StringField('First Name', validators=[Optional()])
    lastname = StringField('Last Name', validators=[Optional()])
    address_line = StringField('Street Address', validators=[Optional()])
    postal_code = StringField('Postal Code', validators=[Optional()])
    region_code = HiddenField('Region Code')
    province_code = HiddenField('Province Code')
    city_code = HiddenField('City Code')
    barangay_code = HiddenField('Barangay Code')
    region_name = SelectField('Region', choices=[], validators=[Optional()])
    province_name = SelectField('Province', choices=[], validators=[Optional()])
    city_name = SelectField('City/Municipality', choices=[], validators=[Optional()])
    barangay_name = SelectField('Barangay', choices=[], validators=[Optional()])
    phone = StringField('Phone Number', validators=[Optional()])
    status = SelectField('Account Status', 
                        choices=[('active', 'Active'), 
                                ('deactivated', 'Deactivated'), 
                                ('pending', 'Pending')],
                        validators=[DataRequired()])
    submit = SubmitField('Update User')

    def __init__(self, original_email, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        email.data = email.data.strip().lower()
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('This email is already in use. Please use a different email address.')

class ConfirmTransferForm(FlaskForm):
    recipient_username = HiddenField('Recipient Username')
    recipient_account = HiddenField('Recipient Account Number')
    amount = HiddenField('Amount')
    transfer_type = HiddenField('Transfer Type')
    submit = SubmitField('Confirm Transfer')