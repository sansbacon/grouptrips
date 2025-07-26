from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(100), unique=True)
    avatar_url = db.Column(db.String(500))
    display_name = db.Column(db.String(100), nullable=False)
    default_timezone = db.Column(db.String(50), default='US/Central')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_local_account = db.Column(db.Boolean, default=False)
    is_test_user = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_password(self):
        return self.password_hash is not None

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timezone = db.Column(db.String(50), default='America/Chicago')
    max_participants = db.Column(db.Integer, default=12)
    final_start_date = db.Column(db.DateTime)
    final_end_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='planning')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organizer = db.relationship('User', backref='organized_trips')

class TripMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # organizer/member/viewer
    rsvp_status = db.Column(db.String(10), default='pending')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    trip = db.relationship('Trip', backref='members')
    user = db.relationship('User', backref='trip_memberships')

class SuggestedDate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trip = db.relationship('Trip', backref='suggested_dates')
    creator = db.relationship('User', backref='suggested_dates')

class DateVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    suggested_date_id = db.Column(db.Integer, db.ForeignKey('suggested_date.id'), nullable=False)
    vote_type = db.Column(db.String(20), nullable=False) # preferred/available/not_available
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='date_votes')
    suggested_date = db.relationship('SuggestedDate', backref='votes')

class HousingOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    estimated_price = db.Column(db.Float)
    listing_link = db.Column(db.String(500))
    description = db.Column(db.Text)
    suggested_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trip = db.relationship('Trip', backref='housing_options')
    suggester = db.relationship('User', backref='suggested_housing')

class HousingVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    housing_option_id = db.Column(db.Integer, db.ForeignKey('housing_option.id'), nullable=False)
    vote_type = db.Column(db.String(20), nullable=False) # preferred/acceptable/not_acceptable
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='housing_votes')
    housing_option = db.relationship('HousingOption', backref='votes')

class ActivityOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    suggested_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trip = db.relationship('Trip', backref='activity_options')
    suggester = db.relationship('User', backref='suggested_activities')

class ActivityVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_option_id = db.Column(db.Integer, db.ForeignKey('activity_option.id'), nullable=False)
    vote_type = db.Column(db.String(20), nullable=False) # preferred/acceptable/not_acceptable
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='activity_votes')
    activity_option = db.relationship('ActivityOption', backref='votes')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Polymorphic relationship to link comments to dates, housing, or activities
    associated_item_type = db.Column(db.String(50))
    associated_item_id = db.Column(db.Integer)

    user = db.relationship('User', backref='comments')
    trip = db.relationship('Trip', backref='comments')
    parent = db.relationship('Comment', remote_side=[id], backref='replies')

class TripInvitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    invitation_code = db.Column(db.String(100), unique=True, nullable=False)
    role_type = db.Column(db.String(20), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expires_at = db.Column(db.DateTime)
    used_at = db.Column(db.DateTime)

    trip = db.relationship('Trip', backref='invitations')
    creator = db.relationship('User', backref='created_invitations')
