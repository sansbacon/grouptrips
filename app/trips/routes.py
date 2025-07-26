from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField, DateField, FloatField, HiddenField, SelectField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
import os
import uuid
from werkzeug.utils import secure_filename
from app import db
from app.models.models import Trip, TripMember, User, SuggestedDate, DateVote, HousingOption, HousingVote, ActivityOption, ActivityVote, Comment, TripInvitation
from functools import wraps
from datetime import datetime
from app.utils.invitations import send_bulk_invitations

trips = Blueprint('trips', __name__)

def save_uploaded_file(file, upload_type):
    """
    Save uploaded file and return the URL path
    upload_type: 'housing' or 'activities'
    """
    from ..utils.file_upload import save_uploaded_file as save_file
    
    if file and file.filename:
        # Use the utility function to save the file
        relative_path = save_file(file, upload_type)
        if relative_path:
            # Convert to URL path for database storage
            return f"/static/{relative_path}"
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session['user_id']
            trip_id = kwargs.get('trip_id') or request.view_args.get('trip_id')
            if not trip_id:
                # Fallback for routes without trip_id in URL, e.g., voting routes
                if 'suggested_date_id' in kwargs:
                    item = SuggestedDate.query.get_or_404(kwargs['suggested_date_id'])
                    trip_id = item.trip_id
                elif 'housing_option_id' in kwargs:
                    item = HousingOption.query.get_or_404(kwargs['housing_option_id'])
                    trip_id = item.trip_id
                elif 'activity_option_id' in kwargs:
                    item = ActivityOption.query.get_or_404(kwargs['activity_option_id'])
                    trip_id = item.trip_id

            trip_member = TripMember.query.filter_by(trip_id=trip_id, user_id=user_id).first()
            if not trip_member or trip_member.role not in role_name:
                flash('You do not have permission to perform this action.', 'error')
                return redirect(url_for('trips.view_trip', trip_id=trip_id))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class EnhancedTripForm(FlaskForm):
    # Step 1: Basic Information
    title = StringField('Trip Title', validators=[DataRequired()], 
                       render_kw={"placeholder": "e.g., Summer Beach Getaway 2025", "required": True})
    description = TextAreaField('Trip Description', 
                               render_kw={"placeholder": "Tell everyone what this trip is about, what you'll do, and what makes it special...", "rows": 4})
    trip_type = SelectField('Trip Type', 
                           choices=[
                               ('vacation', '🏖️ Vacation'),
                               ('adventure', '🏔️ Adventure'),
                               ('business', '💼 Business'),
                               ('family', '👨‍👩‍👧‍👦 Family'),
                               ('friends', '👥 Friends'),
                               ('romantic', '💕 Romantic'),
                               ('solo', '🚶 Solo'),
                               ('other', '🎯 Other')
                           ], 
                           validators=[DataRequired()],
                           default='vacation',
                           render_kw={"required": True})
    privacy_level = SelectField('Privacy Level',
                               choices=[
                                   ('private', '🔒 Private - Invite only'),
                                   ('invite-only', '📧 Invite only with link sharing'),
                                   ('public', '🌍 Public - Anyone can find')
                               ],
                               validators=[DataRequired()],
                               default='private',
                               render_kw={"required": True})
    
    # Step 2: Destination & Details
    destination = StringField('Destination', validators=[DataRequired()],
                             render_kw={"placeholder": "e.g., Cancun, Mexico or Paris, France", "required": True})
    estimated_budget_per_person = FloatField('Estimated Budget per Person ($)', 
                                           validators=[Optional(), NumberRange(min=0, max=100000)],
                                           render_kw={"placeholder": "1500", "min": "0", "max": "100000"})
    max_participants = IntegerField('Maximum Participants', 
                                   validators=[Optional(), NumberRange(min=2, max=50)],
                                   default=12,
                                   render_kw={"placeholder": "12", "min": "2", "max": "50"})
    
    # Step 3: Initial Dates (optional)
    suggested_start_date = DateField('Suggested Start Date', validators=[Optional()], format='%Y-%m-%d')
    suggested_end_date = DateField('Suggested End Date', validators=[Optional()], format='%Y-%m-%d')
    
    # Step 4: Initial Invitees (optional)
    initial_invitees = TextAreaField('Initial Invitees (optional)', 
                                   render_kw={"placeholder": "john@email.com, jane@email.com, friend@example.com", "rows": 4})
    
    # Form navigation
    current_step = HiddenField('Current Step', default='1')
    submit = SubmitField('🚀 Create Trip')
    
    def validate_suggested_end_date(self, field):
        if field.data and self.suggested_start_date.data:
            if field.data < self.suggested_start_date.data:
                raise ValidationError('End date must be after start date.')
    
    def validate_initial_invitees(self, field):
        if field.data:
            import re
            emails = [email.strip() for email in field.data.split(',') if email.strip()]
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            
            for email in emails:
                if not email_pattern.match(email):
                    raise ValidationError(f'Invalid email address: {email}')
            
            if len(emails) > 20:
                raise ValidationError('You can invite a maximum of 20 people at once.')

class SuggestedDateForm(FlaskForm):
    start_date = DateField('Start Date', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Suggest Date')

class HousingOptionForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    location = StringField('Location')
    estimated_price = FloatField('Estimated Price', validators=[Optional()])
    listing_link = StringField('Listing Link')
    description = TextAreaField('Description')
    image = FileField('Photo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Suggest Housing')

class ActivityOptionForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    image = FileField('Photo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Suggest Activity')

class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    parent_comment_id = HiddenField('Parent Comment ID')
    associated_item_type = HiddenField('Associated Item Type')
    associated_item_id = HiddenField('Associated Item ID')
    submit = SubmitField('Add Comment')

class InvitationForm(FlaskForm):
    emails = TextAreaField('Emails (comma-separated)', validators=[DataRequired()])
    role = SelectField('Role', choices=[('member', 'Member'), ('viewer', 'Viewer')], validators=[DataRequired()])
    submit = SubmitField('Send Invitations')

@trips.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user = User.query.get(user_id)
    user_trips = db.session.query(Trip).join(TripMember).filter(TripMember.user_id == user_id).all()
    return render_template('trips/dashboard.html', trips=user_trips)

@trips.route('/create', methods=['GET', 'POST'])
@login_required
def create_trip():
    form = EnhancedTripForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        
        # Create the trip with all the enhanced fields
        trip = Trip(
            title=form.title.data,
            description=form.description.data,
            destination=form.destination.data,
            trip_type=form.trip_type.data,
            privacy_level=form.privacy_level.data,
            estimated_budget_per_person=form.estimated_budget_per_person.data,
            max_participants=form.max_participants.data or 12,
            organizer_id=user_id
        )
        db.session.add(trip)
        db.session.commit()

        # Add the organizer as a member
        trip_member = TripMember(
            trip_id=trip.id,
            user_id=user_id,
            role='organizer'
        )
        db.session.add(trip_member)
        
        # Add initial suggested dates if provided
        if form.suggested_start_date.data and form.suggested_end_date.data:
            suggested_date = SuggestedDate(
                trip_id=trip.id,
                start_date=datetime.combine(form.suggested_start_date.data, datetime.min.time()),
                end_date=datetime.combine(form.suggested_end_date.data, datetime.min.time()),
                created_by=user_id
            )
            db.session.add(suggested_date)
        
        db.session.commit()

        # Handle initial invitees if provided
        if form.initial_invitees.data:
            try:
                from app.utils.invitations import send_bulk_invitations
                user = User.query.get(user_id)
                emails = [email.strip() for email in form.initial_invitees.data.split(',') if email.strip()]
                if emails:
                    results = send_bulk_invitations(trip, user, emails, 'member')
                    flash(f"Trip created successfully! Invitations sent: {results['email_sent']} successful, {results['email_failed']} failed.", 'success')
                else:
                    flash('Trip created successfully!', 'success')
            except Exception as e:
                flash('Trip created successfully, but there was an issue sending invitations.', 'info')
        else:
            flash('Trip created successfully!', 'success')
            
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    
    return render_template('trips/create_trip_matched.html', form=form)

@trips.route('/create-test', methods=['GET', 'POST'])
@login_required
def create_trip_test():
    """Temporary route for testing the original complex create trip page"""
    form = EnhancedTripForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        
        # Create the trip with all the enhanced fields
        trip = Trip(
            title=form.title.data,
            description=form.description.data,
            destination=form.destination.data,
            trip_type=form.trip_type.data,
            privacy_level=form.privacy_level.data,
            estimated_budget_per_person=form.estimated_budget_per_person.data,
            max_participants=form.max_participants.data or 12,
            organizer_id=user_id
        )
        db.session.add(trip)
        db.session.commit()

        # Add the organizer as a member
        trip_member = TripMember(
            trip_id=trip.id,
            user_id=user_id,
            role='organizer'
        )
        db.session.add(trip_member)
        
        # Add initial suggested dates if provided
        if form.suggested_start_date.data and form.suggested_end_date.data:
            suggested_date = SuggestedDate(
                trip_id=trip.id,
                start_date=datetime.combine(form.suggested_start_date.data, datetime.min.time()),
                end_date=datetime.combine(form.suggested_end_date.data, datetime.min.time()),
                created_by=user_id
            )
            db.session.add(suggested_date)
        
        db.session.commit()

        # Handle initial invitees if provided
        if form.initial_invitees.data:
            try:
                from app.utils.invitations import send_bulk_invitations
                user = User.query.get(user_id)
                emails = [email.strip() for email in form.initial_invitees.data.split(',') if email.strip()]
                if emails:
                    results = send_bulk_invitations(trip, user, emails, 'member')
                    flash(f"Trip created successfully! Invitations sent: {results['email_sent']} successful, {results['email_failed']} failed.", 'success')
                else:
                    flash('Trip created successfully!', 'success')
            except Exception as e:
                flash('Trip created successfully, but there was an issue sending invitations.', 'info')
        else:
            flash('Trip created successfully!', 'success')
            
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    
    return render_template('trips/create_trip.html', form=form)

@trips.route('/<int:trip_id>', methods=['GET', 'POST'])
@login_required
@role_required(['organizer', 'member', 'viewer'])
def view_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    date_form = SuggestedDateForm(prefix='date')
    housing_form = HousingOptionForm(prefix='housing')
    activity_form = ActivityOptionForm(prefix='activity')
    comment_form = CommentForm(prefix='comment')

    if date_form.validate_on_submit() and date_form.submit.data:
        user_id = session['user_id']
        suggested_date = SuggestedDate(
            trip_id=trip.id,
            start_date=datetime.combine(date_form.start_date.data, datetime.min.time()),
            end_date=datetime.combine(date_form.end_date.data, datetime.min.time()),
            created_by=user_id
        )
        db.session.add(suggested_date)
        db.session.commit()
        flash('Date suggested successfully!', 'success')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))

    if housing_form.validate_on_submit() and housing_form.submit.data:
        user_id = session['user_id']
        
        # Handle image upload
        image_url = None
        if housing_form.image.data:
            image_url = save_uploaded_file(housing_form.image.data, 'housing')
        
        housing_option = HousingOption(
            trip_id=trip.id,
            name=housing_form.name.data,
            location=housing_form.location.data,
            estimated_price=housing_form.estimated_price.data,
            listing_link=housing_form.listing_link.data,
            description=housing_form.description.data,
            image_url=image_url,
            suggested_by_user_id=user_id
        )
        db.session.add(housing_option)
        db.session.commit()
        flash('Housing option suggested successfully!', 'success')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))

    if activity_form.validate_on_submit() and activity_form.submit.data:
        user_id = session['user_id']
        
        # Handle image upload
        image_url = None
        if activity_form.image.data:
            image_url = save_uploaded_file(activity_form.image.data, 'activities')
        
        activity_option = ActivityOption(
            trip_id=trip.id,
            name=activity_form.name.data,
            description=activity_form.description.data,
            image_url=image_url,
            suggested_by_user_id=user_id
        )
        db.session.add(activity_option)
        db.session.commit()
        flash('Activity option suggested successfully!', 'success')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))

    if comment_form.validate_on_submit() and comment_form.submit.data:
        user_id = session['user_id']
        comment = Comment(
            user_id=user_id,
            trip_id=trip.id,
            content=comment_form.content.data,
            parent_comment_id=comment_form.parent_comment_id.data or None,
            associated_item_type=comment_form.associated_item_type.data,
            associated_item_id=comment_form.associated_item_id.data
        )
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))

    suggested_dates = SuggestedDate.query.filter_by(trip_id=trip.id).all()
    housing_options = HousingOption.query.filter_by(trip_id=trip.id).all()
    activity_options = ActivityOption.query.filter_by(trip_id=trip.id).all()
    comments = Comment.query.filter_by(trip_id=trip.id).order_by(Comment.created_at.asc()).all()
    return render_template('trips/view_trip.html', trip=trip, date_form=date_form, housing_form=housing_form, activity_form=activity_form, comment_form=comment_form, suggested_dates=suggested_dates, housing_options=housing_options, activity_options=activity_options, comments=comments)

@trips.route('/vote_date/<int:suggested_date_id>/<vote_type>')
@login_required
@role_required(['organizer', 'member'])
def vote_date(suggested_date_id, vote_type):
    user_id = session['user_id']
    suggested_date = SuggestedDate.query.get_or_404(suggested_date_id)
    
    # Check if user has already voted
    existing_vote = DateVote.query.filter_by(user_id=user_id, suggested_date_id=suggested_date_id).first()

    if existing_vote:
        existing_vote.vote_type = vote_type
    else:
        new_vote = DateVote(
            user_id=user_id,
            suggested_date_id=suggested_date_id,
            vote_type=vote_type
        )
        db.session.add(new_vote)
    
    db.session.commit()
    flash('Your vote has been recorded.', 'success')
    return redirect(url_for('trips.view_trip', trip_id=suggested_date.trip_id))

@trips.route('/vote_housing/<int:housing_option_id>/<vote_type>')
@login_required
@role_required(['organizer', 'member'])
def vote_housing(housing_option_id, vote_type):
    user_id = session['user_id']
    housing_option = HousingOption.query.get_or_404(housing_option_id)
    
    # Check if user has already voted
    existing_vote = HousingVote.query.filter_by(user_id=user_id, housing_option_id=housing_option_id).first()

    if existing_vote:
        existing_vote.vote_type = vote_type
    else:
        new_vote = HousingVote(
            user_id=user_id,
            housing_option_id=housing_option_id,
            vote_type=vote_type
        )
        db.session.add(new_vote)
    
    db.session.commit()
    flash('Your vote has been recorded.', 'success')
    return redirect(url_for('trips.view_trip', trip_id=housing_option.trip_id))

@trips.route('/vote_activity/<int:activity_option_id>/<vote_type>')
@login_required
@role_required(['organizer', 'member'])
def vote_activity(activity_option_id, vote_type):
    user_id = session['user_id']
    activity_option = ActivityOption.query.get_or_404(activity_option_id)
    
    # Check if user has already voted
    existing_vote = ActivityVote.query.filter_by(user_id=user_id, activity_option_id=activity_option_id).first()

    if existing_vote:
        existing_vote.vote_type = vote_type
    else:
        new_vote = ActivityVote(
            user_id=user_id,
            activity_option_id=activity_option_id,
            vote_type=vote_type
        )
        db.session.add(new_vote)
    
    db.session.commit()
    flash('Your vote has been recorded.', 'success')
    return redirect(url_for('trips.view_trip', trip_id=activity_option.trip_id))

@trips.route('/<int:trip_id>/invite', methods=['GET', 'POST'])
@login_required
@role_required(['organizer'])
def invite_to_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    form = InvitationForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        user = User.query.get(user_id)
        emails = [email.strip() for email in form.emails.data.split(',')]
        role = form.role.data
        results = send_bulk_invitations(trip, user, emails, role)
        flash(f"Invitations sent: {results['email_sent']} successful, {results['email_failed']} failed.", 'info')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    return render_template('trips/invite_to_trip.html', trip=trip, form=form)

@trips.route('/join/<invitation_code>')
@login_required
def join_trip(invitation_code):
    invitation = TripInvitation.query.filter_by(invitation_code=invitation_code).first_or_404()
    if invitation.used_at:
        flash('This invitation has already been used.', 'error')
        return redirect(url_for('trips.dashboard'))
    if invitation.expires_at < datetime.utcnow():
        flash('This invitation has expired.', 'error')
        return redirect(url_for('trips.dashboard'))

    user_id = session['user_id']
    
    # Check if user is already a member
    existing_member = TripMember.query.filter_by(trip_id=invitation.trip_id, user_id=user_id).first()
    if existing_member:
        flash('You are already a member of this trip.', 'info')
        return redirect(url_for('trips.view_trip', trip_id=invitation.trip_id))

    trip_member = TripMember(
        trip_id=invitation.trip_id,
        user_id=user_id,
        role=invitation.role_type
    )
    db.session.add(trip_member)
    invitation.used_at = datetime.utcnow()
    db.session.commit()

    flash('You have successfully joined the trip!', 'success')
    return redirect(url_for('trips.view_trip', trip_id=invitation.trip_id))
