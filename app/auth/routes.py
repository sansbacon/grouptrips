"""Authentication routes for the GroupTrips application."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length
from app import db, google
from app.models.models import User, TripInvitation, TripMember
from app.utils.email import send_login_email
from app.utils.oauth import handle_google_callback
import secrets

auth = Blueprint('auth', __name__)


class LoginForm(FlaskForm):
    """Form for user login."""
    username_or_email = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[])
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    """Form for user registration."""
    display_name = StringField('Display Name', validators=[DataRequired(), Length(min=1, max=50)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - handles both username and email login with password."""
    form = LoginForm()
    if form.validate_on_submit():
        username_or_email = form.username_or_email.data.strip()
        password = form.password.data
        
        # Try to find user by username first, then by email
        user = User.query.filter_by(username=username_or_email).first()
        if not user:
            user = User.query.filter_by(email=username_or_email.lower()).first()
        
        if not user:
            flash('No account found with that username or email. Please register first.', 'error')
            return redirect(url_for('auth.register'))
        
        # If password is provided, check for local account login
        if password:
            if user.is_local_account and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                flash(f'Welcome back, {user.display_name}!', 'success')
                
                # Redirect admin users to admin dashboard, others to trips dashboard
                if user.is_admin:
                    return redirect(url_for('admin.dashboard'))
                else:
                    return redirect(url_for('trips.dashboard'))
            else:
                flash('Invalid username/email or password.', 'error')
                return render_template('auth/login.html', form=form)
        else:
            # Email-only login for non-local accounts
            if user.is_local_account:
                flash('This account requires a password. Please enter your password.', 'error')
                return render_template('auth/login.html', form=form)
            
            # This part would require a LoginToken model for email-based login
            # For now, we'll just log the user in directly for simplicity
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Logged in successfully!', 'success')
            return redirect(url_for('trips.dashboard'))

    return render_template('auth/login.html', form=form)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page for new users."""
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.lower().strip()
        display_name = form.display_name.data.strip()

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('auth/register.html', form=form)
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('auth.login'))

        user = User(
            username=username,
            email=email,
            display_name=display_name,
            is_local_account=True
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Handle invitation
        invitation_code = request.args.get('invite')
        if invitation_code:
            invitation = TripInvitation.query.filter_by(invitation_code=invitation_code).first()
            if invitation and invitation.expires_at > datetime.utcnow() and not invitation.used_at:
                trip_member = TripMember(
                    trip_id=invitation.trip_id,
                    user_id=user.id,
                    role=invitation.role_type
                )
                db.session.add(trip_member)
                invitation.used_at = datetime.utcnow()
                db.session.commit()
                flash(f'Registration successful! You have been added to the trip.', 'success')
                return redirect(url_for('trips.view_trip', trip_id=invitation.trip_id))

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/logout')
def logout():
    """Logout current user."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth.route('/google-login')
def google_login():
    """Initiate Google OAuth login."""
    if not google:
        flash('Google login is not configured.', 'error')
        return redirect(url_for('auth.login'))
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@auth.route('/google-callback')
def google_callback():
    """Handle Google OAuth callback."""
    if not google:
        flash('Google login is not configured.', 'error')
        return redirect(url_for('auth.login'))
    
    success, result = handle_google_callback(google, request)
    if success:
        user = result
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        flash(f'Welcome, {user.display_name}!', 'success')
        return redirect(url_for('trips.dashboard'))
    else:
        flash(f'Google login failed: {result}', 'error')
        return redirect(url_for('auth.login'))
