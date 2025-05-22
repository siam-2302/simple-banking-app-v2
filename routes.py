from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from app import app, csrf
from extensions import db, limiter
from forms import LoginForm, RegistrationForm, TransferForm, ResetPasswordRequestForm, ResetPasswordForm, DepositForm, UserEditForm, ConfirmTransferForm
from models import User, Transaction
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import os
from functools import wraps
import psgc_api
import datetime

# Context processor to provide current year to all templates
@app.context_processor
def inject_year():
    return {'current_year': datetime.datetime.now().year}

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be an admin to access this page.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Manager required decorator
def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_manager:
            flash('You need to be a manager to access this page.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Email functionality (simulated for this example)
def send_password_reset_email(user):
    # In a real app, this would send an actual email with a reset token
    # For simplicity, we're just creating the token and displaying it
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    token = serializer.dumps(user.email, salt='password-reset')
    reset_url = url_for('reset_password', token=token, _external=True)
    flash(f'Password reset link (would be emailed): {reset_url}')

@app.route('/')
@app.route('/index')
@login_required
def index():
    if current_user.status != 'active' and not current_user.is_admin and not current_user.is_manager:
        flash('Your account is awaiting approval from an administrator.')
        logout_user()
        return redirect(url_for('login'))
    return render_template('index.html', title='Home')

@app.route('/about')
def about():
    return render_template('about.html', title='About Us')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # Check if this is an old SHA-256 password hash (exactly 64 characters)
        # SHA-256 hashes are 64 characters long, bcrypt hashes start with $2b$
        if user and user.password_hash and len(user.password_hash) == 64 and not user.password_hash.startswith('$2b$'):
            import hashlib
            # Verify with old method
            sha2_hash = hashlib.sha256(form.password.data.encode()).hexdigest()
            if sha2_hash == user.password_hash:
                # Upgrade to bcrypt
                user.set_password(form.password.data)
                db.session.commit()
                # Continue with login
            else:
                flash('Invalid username or password')
                return redirect(url_for('login'))
        elif user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        
        # Check if user account is active (unless they're an admin or manager)
        if user.status != 'active' and not user.is_admin and not user.is_manager:
            if user.status == 'pending':
                flash('Your account is awaiting approval from an administrator.')
            else:  # deactivated
                flash('Your account has been deactivated. Please contact an administrator.')
            return redirect(url_for('login'))
            
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, status='pending')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been registered and is awaiting admin approval.')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/account')
@login_required
def account():
    if current_user.status != 'active' and not current_user.is_admin and not current_user.is_manager:
        flash('Your account is awaiting approval from an administrator.')
        logout_user()
        return redirect(url_for('login'))
    transactions = current_user.get_recent_transactions()
    return render_template('account.html', title='Account', transactions=transactions)

@app.route('/transfer', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per hour")
def transfer():
    if current_user.status != 'active' and not current_user.is_admin and not current_user.is_manager:
        flash('Your account is awaiting approval from an administrator.')
        return redirect(url_for('index'))
        
    form = TransferForm()
    if form.validate_on_submit():
        # Find recipient based on transfer type
        recipient = None
        if form.transfer_type.data == 'username':
            recipient = User.query.filter_by(username=form.recipient_username.data).first()
        else:  # account
            recipient = User.query.filter_by(account_number=form.recipient_account.data).first()
            
        amount = form.amount.data
        
        # Check for self-transfer
        if recipient and recipient.id == current_user.id:
            flash('You cannot transfer money to yourself.')
            return redirect(url_for('transfer'))
            
        if current_user.balance < amount:
            flash('Insufficient funds for this transfer.')
            return redirect(url_for('transfer'))
        
        # Check if recipient account is active
        if recipient.status != 'active' and not recipient.is_admin and not recipient.is_manager:
            flash('The recipient account is not active.')
            return redirect(url_for('transfer'))
        
        # Create confirm transfer form with pre-populated data
        confirm_form = ConfirmTransferForm(
            recipient_username=recipient.username,
            recipient_account=recipient.account_number,
            amount=amount,
            transfer_type=form.transfer_type.data
        )
        
        # Show confirmation page before completing transfer
        return render_template('confirm_transfer.html', 
                              recipient=recipient,
                              amount=amount,
                              form=confirm_form)
    
    return render_template('transfer.html', title='Transfer Money', form=form)

@app.route('/execute_transfer', methods=['POST'])
@login_required
@limiter.limit("20 per hour")
def execute_transfer():
    if current_user.status != 'active' and not current_user.is_admin and not current_user.is_manager:
        flash('Your account is awaiting approval from an administrator.')
        return redirect(url_for('index'))
    
    form = ConfirmTransferForm()
    if form.validate_on_submit():
        amount = float(form.amount.data)
        
        # Find recipient based on transfer type
        recipient = None
        if form.transfer_type.data == 'username':
            recipient = User.query.filter_by(username=form.recipient_username.data).first()
        else:  # account
            recipient = User.query.filter_by(account_number=form.recipient_account.data).first()
        
        if recipient is None:
            flash('Recipient not found.')
            return redirect(url_for('transfer'))
        
        # Check if recipient account is active
        if recipient.status != 'active' and not recipient.is_admin and not recipient.is_manager:
            flash('The recipient account is not active.')
            return redirect(url_for('transfer'))
        
        if current_user.transfer_money(recipient, amount):
            db.session.commit()
            flash(f'Successfully transferred ₱{amount:.2f} to {recipient.username}')
            return redirect(url_for('account'))
        else:
            flash('Transfer failed. Please check your balance.')
            return redirect(url_for('transfer'))
    
    return redirect(url_for('transfer'))

@app.route('/reset_password_request', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', title='Reset Password', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    try:
        serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        email = serializer.loads(token, salt='password-reset', max_age=3600)
        user = User.query.filter_by(email=email).first()
        if not user:
            return redirect(url_for('index'))
    except SignatureExpired:
        flash('The password reset link has expired.')
        return redirect(url_for('reset_password_request'))
    except:
        flash('Invalid reset link')
        return redirect(url_for('reset_password_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)

# Admin routes
@app.route('/admin')
@login_required
@admin_required
@limiter.limit("60 per hour")
def admin_dashboard():
    # Regular admins can only see regular users
    if current_user.is_manager:
        # Managers can see all regular users
        users = User.query.filter(User.is_admin.is_(False)).all()
    else:
        # Regular admins can only see regular users (not managers or other admins)
        users = User.query.filter(User.is_admin.is_(False), User.is_manager.is_(False)).all()
    
    return render_template('admin/dashboard.html', title='Admin Dashboard', users=users)

@app.route('/admin/activate_user/<int:user_id>')
@login_required
@admin_required
def activate_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Ensure admin can only activate/deactivate users they can manage
    if not current_user.can_manage_user(user):
        flash('You do not have permission to manage this user.')
        return redirect(url_for('admin_dashboard'))
        
    user.status = 'active'
    db.session.commit()
    flash(f'Account {user.username} has been activated.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/deactivate_user/<int:user_id>')
@login_required
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Ensure admin can only activate/deactivate users they can manage
    if not current_user.can_manage_user(user):
        flash('You do not have permission to manage this user.')
        return redirect(url_for('admin_dashboard'))
        
    user.status = 'deactivated'
    db.session.commit()
    flash(f'Account {user.username} has been deactivated.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/create_account', methods=['GET', 'POST'])
@login_required
@admin_required
@limiter.limit("20 per hour")
def create_account():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, status='active')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('User account has been created.')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/create_account.html', title='Create User Account', form=form)

@app.route('/admin/deposit', methods=['GET', 'POST'])
@login_required
@admin_required
@limiter.limit("30 per hour")
def admin_deposit():
    form = DepositForm()
    
    # Handle account lookup from query parameters (for the lookup button)
    account_details = None
    if request.args.get('account_number'):
        account_number = request.args.get('account_number')
        account_details = User.query.filter_by(account_number=account_number).first()
    
    if form.validate_on_submit():
        user = User.query.filter_by(account_number=form.account_number.data).first()
        if not user:
            flash('User not found')
            return redirect(url_for('admin_deposit'))
        
        # Admin can only deposit to active accounts (or admin/manager accounts)
        if user.status != 'active' and not user.is_admin and not user.is_manager:
            flash('Cannot deposit to inactive account.')
            return redirect(url_for('admin_deposit'))
        
        amount = form.amount.data
        
        # Call deposit method
        if user.deposit(amount, current_user):
            db.session.commit()
            flash(f'Successfully deposited ₱{amount:.2f} to {user.username}')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Deposit failed.')
            return redirect(url_for('admin_deposit'))
    
    return render_template('admin/deposit.html', title='Deposit Funds', form=form, account_details=account_details)

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    from forms import UserEditForm  # Import here to avoid circular imports
    
    user = User.query.get_or_404(user_id)
    
    # Ensure admin can only edit users they can manage
    if not current_user.can_manage_user(user):
        flash('You do not have permission to edit this user.')
        return redirect(url_for('admin_dashboard'))
    
    form = UserEditForm(user.email)
    
    # Load region choices for dropdown (always needed)
    regions = psgc_api.get_regions()
    form.region_name.choices = [('', '-- Select Region --')] + [(r['code'], r['name']) for r in regions]
    
    # Always populate form on both GET and POST to maintain choices
    form.email.data = user.email if form.email.data is None else form.email.data
    form.firstname.data = user.firstname if form.firstname.data is None else form.firstname.data
    form.lastname.data = user.lastname if form.lastname.data is None else form.lastname.data
    form.address_line.data = user.address_line if form.address_line.data is None else form.address_line.data
    form.postal_code.data = user.postal_code if form.postal_code.data is None else form.postal_code.data
    form.phone.data = user.phone if form.phone.data is None else form.phone.data
    form.status.data = user.status if form.status.data is None else form.status.data
    
    # CRITICAL: We need to populate the dependent dropdown choices
    # for both GET and POST requests to avoid validation errors
    
    # Load existing region selection
    region_code = user.region_code
    if form.region_name.data:
        region_code = form.region_name.data
    
    # If we have a region, load provinces
    if region_code:
        provinces = psgc_api.get_provinces(region_code)
        form.province_name.choices = [('', '-- Select Province --')] + [(p['code'], p['name']) for p in provinces]
        
        # Load existing province selection
        province_code = user.province_code
        if form.province_name.data:
            province_code = form.province_name.data
        
        # If we have a province, load cities/municipalities
        if province_code:
            cities = psgc_api.get_cities(province_code)
            municipalities = psgc_api.get_municipalities(province_code)
            city_choices = [('', '-- Select City/Municipality --')]
            
            # Add cities
            for city in cities:
                city_choices.append((city['code'], f"{city['name']} (City)"))
            
            # Add municipalities
            for municipality in municipalities:
                city_choices.append((municipality['code'], municipality['name']))
            
            form.city_name.choices = city_choices
            
            # Load existing city selection
            city_code = user.city_code
            if form.city_name.data:
                city_code = form.city_name.data
            
            # If we have a city, load barangays
            if city_code:
                barangays = []
                # Check if it's a city or municipality
                city_info = psgc_api.get_city_by_code(city_code)
                if city_info:
                    barangays = psgc_api.get_barangays(city_code=city_code)
                else:
                    barangays = psgc_api.get_barangays(municipality_code=city_code)
                
                form.barangay_name.choices = [('', '-- Select Barangay --')] + [(b['code'], b['name']) for b in barangays]
    else:
        # If no region selected, provide empty choices for dependent fields
        form.province_name.choices = [('', '-- Select Province --')]
        form.city_name.choices = [('', '-- Select City/Municipality --')]
        form.barangay_name.choices = [('', '-- Select Barangay --')]
    
    # Only on GET request, set the selected values
    if request.method == 'GET':
        if user.region_code:
            form.region_code.data = user.region_code
            form.region_name.data = user.region_code
            
        if user.province_code:
            form.province_code.data = user.province_code
            form.province_name.data = user.province_code
            
        if user.city_code:
            form.city_code.data = user.city_code
            form.city_name.data = user.city_code
            
        if user.barangay_code:
            form.barangay_code.data = user.barangay_code
            form.barangay_name.data = user.barangay_code
    
    if form.validate_on_submit():
        # Track changes to create an audit record
        changes = []
        if user.email != form.email.data:
            changes.append(f"Email: {user.email} → {form.email.data}")
        if user.firstname != form.firstname.data:
            changes.append(f"First Name: {user.firstname or 'None'} → {form.firstname.data or 'None'}")
        if user.lastname != form.lastname.data:
            changes.append(f"Last Name: {user.lastname or 'None'} → {form.lastname.data or 'None'}")
        if user.address_line != form.address_line.data:
            changes.append(f"Address Line: {user.address_line or 'None'} → {form.address_line.data or 'None'}")
        if user.phone != form.phone.data:
            changes.append(f"Phone: {user.phone or 'None'} → {form.phone.data or 'None'}")
        if user.status != form.status.data:
            changes.append(f"Status: {user.status} → {form.status.data}")
            
        # Address fields changes
        if form.region_name.data and form.region_name.data != '' and form.region_name.data != user.region_code:
            region = psgc_api.get_region_by_code(form.region_name.data)
            region_name = region['name'] if region else form.region_name.data
            changes.append(f"Region: {user.region_name or 'None'} → {region_name}")
            
        if form.province_name.data and form.province_name.data != '' and form.province_name.data != user.province_code:
            province = psgc_api.get_province_by_code(form.province_name.data)
            province_name = province['name'] if province else form.province_name.data
            changes.append(f"Province: {user.province_name or 'None'} → {province_name}")
            
        if form.city_name.data and form.city_name.data != '' and form.city_name.data != user.city_code:
            city = psgc_api.get_city_by_code(form.city_name.data)
            municipality = None if city else psgc_api.get_municipality_by_code(form.city_name.data)
            city_name = city['name'] if city else (municipality['name'] if municipality else form.city_name.data)
            changes.append(f"City/Municipality: {user.city_name or 'None'} → {city_name}")
            
        if form.barangay_name.data and form.barangay_name.data != '' and form.barangay_name.data != user.barangay_code:
            barangay = psgc_api.get_barangay_by_code(form.barangay_name.data)
            barangay_name = barangay['name'] if barangay else form.barangay_name.data
            changes.append(f"Barangay: {user.barangay_name or 'None'} → {barangay_name}")
            
        if user.postal_code != form.postal_code.data:
            changes.append(f"Postal Code: {user.postal_code or 'None'} → {form.postal_code.data or 'None'}")
        
        # Update user information
        user.email = form.email.data
        user.firstname = form.firstname.data
        user.lastname = form.lastname.data
        user.address_line = form.address_line.data
        user.postal_code = form.postal_code.data
        user.phone = form.phone.data
        user.status = form.status.data
        
        # Update address data with names and codes
        if form.region_name.data and form.region_name.data != '':
            user.region_code = form.region_name.data
            region = psgc_api.get_region_by_code(form.region_name.data)
            if region:
                user.region_name = region['name']
        else:
            user.region_code = None
            user.region_name = None
            
        if form.province_name.data and form.province_name.data != '':
            user.province_code = form.province_name.data
            province = psgc_api.get_province_by_code(form.province_name.data)
            if province:
                user.province_name = province['name']
        else:
            user.province_code = None
            user.province_name = None
            
        if form.city_name.data and form.city_name.data != '':
            user.city_code = form.city_name.data
            # Check if it's a city
            city = psgc_api.get_city_by_code(form.city_name.data)
            if city:
                user.city_name = city['name']
            else:
                # Must be a municipality
                municipality = psgc_api.get_municipality_by_code(form.city_name.data)
                if municipality:
                    user.city_name = municipality['name']
        else:
            user.city_code = None
            user.city_name = None
            
        if form.barangay_name.data and form.barangay_name.data != '':
            user.barangay_code = form.barangay_name.data
            barangay = psgc_api.get_barangay_by_code(form.barangay_name.data)
            if barangay:
                user.barangay_name = barangay['name']
        else:
            user.barangay_code = None
            user.barangay_name = None
        
        # Create audit record if there were changes
        if changes:
            # Create a transaction record for the user edit
            transaction = Transaction(
                sender_id=current_user.id,  # Admin making the change
                receiver_id=user.id,        # User being modified
                amount=None,                # No money involved
                transaction_type='user_edit',
                details="\n".join(changes),
                timestamp=datetime.datetime.utcnow()
            )
            db.session.add(transaction)
        
        db.session.commit()
        flash(f'User information for {user.username} has been updated.')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_user.html', title='Edit User', form=form, user=user)

# Apply rate limiting to API endpoints
@app.route('/api/provinces/<region_code>')
@login_required
@admin_required
@limiter.limit("30 per minute")
def get_provinces(region_code):
    provinces = psgc_api.get_provinces(region_code)
    return jsonify([{'code': p['code'], 'name': p['name']} for p in provinces])

@app.route('/api/cities/<province_code>')
@login_required
@admin_required
@limiter.limit("30 per minute")
def get_cities_and_municipalities(province_code):
    # Check if it's a city or municipality
    cities = psgc_api.get_cities(province_code)
    municipalities = psgc_api.get_municipalities(province_code)
    
    result = []
    
    # Add cities
    for city in cities:
        result.append({'code': city['code'], 'name': f"{city['name']} (City)"})
    
    # Add municipalities
    for municipality in municipalities:
        result.append({'code': municipality['code'], 'name': municipality['name']})
        
    return jsonify(result)

@app.route('/api/barangays/<city_code>')
@login_required
@admin_required
@limiter.limit("30 per minute")
def get_barangays(city_code):
    # Check if it's a city or municipality
    city_info = psgc_api.get_city_by_code(city_code)
    
    barangays = []
    if city_info:
        barangays = psgc_api.get_barangays(city_code=city_code)
    else:
        # Must be a municipality
        barangays = psgc_api.get_barangays(municipality_code=city_code)
        
    return jsonify([{'code': b['code'], 'name': b['name']} for b in barangays])

# Manager routes
@app.route('/manager')
@login_required
@manager_required
@limiter.limit("60 per hour")
def manager_dashboard():
    # Managers can see all admins and regular users, but not other managers
    admins = User.query.filter_by(is_admin=True, is_manager=False).all()
    regular_users = User.query.filter_by(is_admin=False, is_manager=False).all()
    
    return render_template('manager/dashboard.html', title='Manager Dashboard', admins=admins, regular_users=regular_users)

@app.route('/manager/create_admin', methods=['GET', 'POST'])
@login_required
@manager_required
@limiter.limit("10 per hour")
def create_admin():
    form = RegistrationForm()
    if form.validate_on_submit():
        admin = User(username=form.username.data, email=form.email.data, status='active', is_admin=True)
        admin.set_password(form.password.data)
        db.session.add(admin)
        db.session.commit()
        flash('Admin account has been created')
        return redirect(url_for('admin_list'))
    return render_template('manager/create_admin.html', title='Create Admin Account', form=form)

@app.route('/manager/toggle_admin/<int:user_id>')
@login_required
@manager_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    # Managers can only modify admins, not other managers
    if user.is_manager:
        flash('You cannot modify another manager account.')
        return redirect(url_for('manager_dashboard'))
    
    # Store original state to determine redirect
    was_admin = user.is_admin
    
    # Toggle admin status
    user.is_admin = not user.is_admin
    
    # If promoting to admin, ensure account is active
    if user.is_admin:
        user.status = 'active'  # Set status to active when promoting to admin
        flash(f'User {user.username} has been promoted to admin.')
        db.session.commit()
        return redirect(url_for('user_list'))
    else:
        flash(f'User {user.username} has been demoted from admin.')
        db.session.commit()
        return redirect(url_for('admin_list'))

@app.route('/manager/user_list')
@login_required
@manager_required
def user_list():
    # Get all users except admins and managers
    users = User.query.filter(User.is_admin.is_(False), User.is_manager.is_(False)).all()
    return render_template('manager/user_list.html', title='All Users', users=users)

@app.route('/manager/admin_list')
@login_required
@manager_required
def admin_list():
    # Get all admin users except managers
    admins = User.query.filter(User.is_admin.is_(True), User.is_manager.is_(False)).all()
    return render_template('manager/admin_list.html', title='All Admin Users', admins=admins)

@app.route('/manager/admin_transactions')
@login_required
@manager_required
def admin_transactions():
    # Get all admin users except managers
    admins = User.query.filter(User.is_admin.is_(True), User.is_manager.is_(False)).all()
    
    # Get all transactions where any admin is either a sender or receiver
    admin_ids = [admin.id for admin in admins]
    
    # Base query
    query = Transaction.query.filter(
        db.or_(
            Transaction.sender_id.in_(admin_ids),
            Transaction.receiver_id.in_(admin_ids)
        )
    )
    
    # Apply search if provided
    search_term = request.args.get('search', '').strip()
    if search_term:
        # Build list of transaction IDs that match search criteria
        matching_transaction_ids = []
        
        # If search term is a number, check transaction ID
        if search_term.isdigit():
            matching_transaction_ids.extend([t.id for t in Transaction.query.filter(Transaction.id == int(search_term)).all()])
        
        # Search by sender username
        sender_matches = Transaction.query.join(
            User, Transaction.sender_id == User.id
        ).filter(
            User.username.ilike(f'%{search_term}%')
        ).all()
        matching_transaction_ids.extend([t.id for t in sender_matches])
        
        # Search by receiver username
        receiver_matches = Transaction.query.join(
            User, Transaction.receiver_id == User.id
        ).filter(
            User.username.ilike(f'%{search_term}%')
        ).all()
        matching_transaction_ids.extend([t.id for t in receiver_matches])
        
        # Search in transaction details
        detail_matches = Transaction.query.filter(
            Transaction.details.ilike(f'%{search_term}%')
        ).all()
        matching_transaction_ids.extend([t.id for t in detail_matches])
        
        # Filter original query to only include matching transactions
        if matching_transaction_ids:
            query = query.filter(Transaction.id.in_(set(matching_transaction_ids)))
        else:
            # If no matches, return empty result
            query = query.filter(Transaction.id == -1)  # Impossible condition to return empty set
    
    # Apply filters
    transaction_type = request.args.get('type')
    admin_role = request.args.get('role')
    admin_id = request.args.get('admin_id')
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    if admin_role == 'sender':
        query = query.filter(Transaction.sender_id.in_(admin_ids))
    elif admin_role == 'receiver':
        query = query.filter(Transaction.receiver_id.in_(admin_ids))
    
    if admin_id and admin_id.isdigit():
        admin_id = int(admin_id)
        query = query.filter(
            db.or_(
                Transaction.sender_id == admin_id,
                Transaction.receiver_id == admin_id
            )
        )
    
    # Get sorted results
    transactions = query.order_by(Transaction.timestamp.desc()).all()
    
    return render_template('manager/admin_transactions.html', 
                         title='Admin Transactions', 
                         transactions=transactions,
                         admins=admins)

@app.route('/manager/transfers')
@login_required
@manager_required
def manager_transfers():
    # Base query - only get transfer transactions
    query = Transaction.query.filter(Transaction.transaction_type == 'transfer')
    
    # Apply search if provided
    search_term = request.args.get('search', '').strip()
    if search_term:
        # Build list of transaction IDs that match search criteria
        matching_transaction_ids = []
        
        # If search term is a number, check transaction ID
        if search_term.isdigit():
            matching_transaction_ids.extend([t.id for t in Transaction.query.filter(Transaction.id == int(search_term)).all()])
        
        # Search by sender username
        sender_matches = Transaction.query.join(
            User, Transaction.sender_id == User.id
        ).filter(
            User.username.ilike(f'%{search_term}%')
        ).all()
        matching_transaction_ids.extend([t.id for t in sender_matches])
        
        # Search by receiver username
        receiver_matches = Transaction.query.join(
            User, Transaction.receiver_id == User.id
        ).filter(
            User.username.ilike(f'%{search_term}%')
        ).all()
        matching_transaction_ids.extend([t.id for t in receiver_matches])
        
        # Search by sender account number
        sender_account_matches = Transaction.query.join(
            User, Transaction.sender_id == User.id
        ).filter(
            User.account_number.ilike(f'%{search_term}%')
        ).all()
        matching_transaction_ids.extend([t.id for t in sender_account_matches])
        
        # Search by receiver account number
        receiver_account_matches = Transaction.query.join(
            User, Transaction.receiver_id == User.id
        ).filter(
            User.account_number.ilike(f'%{search_term}%')
        ).all()
        matching_transaction_ids.extend([t.id for t in receiver_account_matches])
        
        # Search by amount (if search term can be converted to float)
        try:
            amount = float(search_term)
            amount_matches = Transaction.query.filter(Transaction.amount == amount).all()
            matching_transaction_ids.extend([t.id for t in amount_matches])
        except ValueError:
            pass
            
        # Filter original query to only include matching transactions
        if matching_transaction_ids:
            query = query.filter(Transaction.id.in_(set(matching_transaction_ids)))
        else:
            # If no matches, return empty result
            query = query.filter(Transaction.id == -1)  # Impossible condition to return empty set
    
    # Apply date range filter if provided
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    if from_date:
        try:
            from_datetime = datetime.datetime.strptime(from_date, '%Y-%m-%d')
            query = query.filter(Transaction.timestamp >= from_datetime)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_datetime = datetime.datetime.strptime(to_date, '%Y-%m-%d')
            # Add one day to include the entire end date
            to_datetime = to_datetime + datetime.timedelta(days=1)
            query = query.filter(Transaction.timestamp < to_datetime)
        except ValueError:
            pass
    
    # Apply amount range filter if provided
    min_amount = request.args.get('min_amount')
    max_amount = request.args.get('max_amount')
    
    if min_amount:
        try:
            min_amount_value = float(min_amount)
            query = query.filter(Transaction.amount >= min_amount_value)
        except ValueError:
            pass
    
    if max_amount:
        try:
            max_amount_value = float(max_amount)
            query = query.filter(Transaction.amount <= max_amount_value)
        except ValueError:
            pass
    
    # Apply user filter if provided
    user_id = request.args.get('user_id')
    user_role = request.args.get('user_role')
    
    if user_id and user_id.isdigit():
        user_id = int(user_id)
        if user_role == 'sender':
            query = query.filter(Transaction.sender_id == user_id)
        elif user_role == 'receiver':
            query = query.filter(Transaction.receiver_id == user_id)
        else:
            # Both sender and receiver
            query = query.filter(
                db.or_(
                    Transaction.sender_id == user_id,
                    Transaction.receiver_id == user_id
                )
            )
    
    # Get all users for filter dropdown
    users = User.query.all()
    
    # Get sorted results
    transactions = query.order_by(Transaction.timestamp.desc()).all()
    
    return render_template('manager/transfers.html', 
                         title='Transfer Transactions', 
                         transactions=transactions,
                         users=users) 