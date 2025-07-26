"""Admin routes for the GroupTrips application."""
from datetime import datetime
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, IntegerField, PasswordField, TextAreaField, DateTimeLocalField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from app import db
from app.models.models import User, Trip, TripMember, TripInvitation
from functools import wraps

admin = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

class UserForm(FlaskForm):
    """Form for editing user details."""
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    display_name = StringField('Display Name', validators=[Length(max=100)])
    is_admin = BooleanField('Admin User')
    is_test_user = BooleanField('Test User')
    submit = SubmitField('Update User')

class SetPasswordForm(FlaskForm):
    """Form for setting admin user passwords."""
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Set Password')

@admin.route('/')
@admin_required
def dashboard():
    """Admin dashboard with enhanced statistics."""
    current_user = get_current_user()
    
    # Basic counts
    total_users = User.query.count()
    total_trips = Trip.query.count()
    total_members = TripMember.query.count()
    total_invitations = TripInvitation.query.count()
    
    # Recent activity (last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_users_count = User.query.filter(User.created_at >= week_ago).count()
    recent_trips_count = Trip.query.filter(Trip.created_at >= week_ago).count()
    
    # Calculate growth percentages (mock data for now - in real app, compare to previous period)
    user_growth = round((recent_users_count / max(total_users, 1)) * 100, 1) if total_users > 0 else 0
    trip_growth = round((recent_trips_count / max(total_trips, 1)) * 100, 1) if total_trips > 0 else 0
    
    # Active members (users who are part of at least one trip)
    active_members = db.session.query(TripMember.user_id).distinct().count()
    
    # System health (simplified)
    system_health = {
        'status': 'healthy',
        'uptime': '99.9%',
        'users_online': 'N/A'  # Would need session tracking for real data
    }
    
    stats = {
        'total_users': total_users,
        'total_trips': total_trips,
        'active_members': active_members,
        'total_invitations': total_invitations,
        'user_growth': user_growth,
        'trip_growth': trip_growth,
        'recent_users_count': recent_users_count,
        'recent_trips_count': recent_trips_count,
        'system_health': system_health
    }
    
    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_trips = Trip.query.order_by(Trip.created_at.desc()).limit(5).all()
    
    # Recent activity combined and sorted
    recent_activity = []
    for user in recent_users:
        recent_activity.append({
            'type': 'user_registered',
            'description': f'New user registered: {user.display_name or user.username}',
            'timestamp': user.created_at,
            'icon': '👥'
        })
    
    for trip in recent_trips:
        recent_activity.append({
            'type': 'trip_created',
            'description': f'Trip created: {trip.title}',
            'timestamp': trip.created_at,
            'icon': '✈️'
        })
    
    # Sort by timestamp and limit to 8 most recent
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:8]

    return render_template('admin/dashboard.html',
                         current_user=current_user,
                         stats=stats,
                         recent_users=recent_users,
                         recent_trips=recent_trips,
                         recent_activity=recent_activity)

@admin.route('/users')
@admin_required
def manage_users():
    """Manage users page."""
    current_user = get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    
    query = User.query
    if search:
        query = query.filter(db.or_(User.username.contains(search), User.email.contains(search), User.display_name.contains(search)))
    
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/users.html', users=users, search=search, current_user=current_user)

@admin.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user details."""
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.display_name = form.display_name.data
        user.is_admin = form.is_admin.data
        user.is_test_user = form.is_test_user.data
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/edit_user.html', form=form, user=user)

@admin.route('/users/<int:user_id>/set-password', methods=['GET', 'POST'])
@admin_required
def set_user_password(user_id):
    """Set password for a user."""
    user = User.query.get_or_404(user_id)
    form = SetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(f'Password set for {user.username}.', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/set_password.html', form=form, user=user)

@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)
    if user.id == get_current_user().id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    # Reassign organized trips or handle as needed
    if user.organized_trips:
        flash(f'User {user.username} organizes trips. Please reassign them before deleting.', 'error')
        return redirect(url_for('admin.manage_users'))

    # Delete user and their trip memberships
    TripMember.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin.route('/trips')
@admin_required
def manage_trips():
    """Manage trips page."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    
    query = Trip.query
    if search:
        query = query.filter(Trip.title.contains(search))
        
    trips = query.order_by(Trip.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin/trips.html', trips=trips, search=search)

@admin.route('/trips/<int:trip_id>/delete', methods=['POST'])
@admin_required
def delete_trip(trip_id):
    """Delete a trip."""
    trip = Trip.query.get_or_404(trip_id)
    # Add more comprehensive deletion logic (e.g., delete related votes, comments)
    db.session.delete(trip)
    db.session.commit()
    flash(f'Trip "{trip.title}" deleted successfully.', 'success')
    return redirect(url_for('admin.manage_trips'))

@admin.route('/system-info')
@admin_required
def system_info():
    """System information page."""
    db_stats = {
        'users': User.query.count(),
        'trips': Trip.query.count(),
        'trip_members': TripMember.query.count(),
        'trip_invitations': TripInvitation.query.count(),
    }
    return render_template('admin/system_info.html', db_stats=db_stats)
