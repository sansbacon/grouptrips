"""Invitation utilities for sending email invitations."""
import re
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any
from flask import url_for, current_app
from app import db
from app.models.models import Trip, TripInvitation, User
from app.utils.email import send_email


def validate_email(email: str) -> bool:
    """Validate email address format.
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if valid email format, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def get_role_description(role_type: str) -> str:
    """Get a description for a given role type."""
    descriptions = {
        'member': 'As a member, you can view trip details, vote on options, and leave comments.',
        'viewer': 'As a viewer, you can see all trip details but cannot vote or comment.',
        'organizer': 'As an organizer, you have full administrative control over the trip.'
    }
    return descriptions.get(role_type, 'You have been invited to this trip.')


def create_invitation_email_content(trip: Trip, sender: User, invitation_code: str, role_type: str) -> Dict[str, str]:
    """Create email content for trip invitation.
    
    Args:
        trip (Trip): Trip to invite to
        sender (User): User sending the invitation
        invitation_code (str): The invitation code
        role_type (str): The role for the invitee
        
    Returns:
        Dict[str, str]: Email subject and body
    """
    invitation_url = url_for('trips.join_trip', invitation_code=invitation_code, _external=True)
    
    from app.utils.timezone import format_datetime_with_timezone
    
    if trip.final_start_date:
        trip_dates = format_datetime_with_timezone(
            trip.final_start_date, trip.timezone, '%B %d, %Y'
        )
    else:
        trip_dates = "Dates to be determined"
        
    subject = f"You're invited to join '{trip.title}' trip!"
    
    body = f"""
Hello!

{sender.display_name} has invited you to join an exciting group trip!

**Trip Details:**
- Trip Name: {trip.title}
- Organizer: {sender.display_name}
- Dates: {trip_dates}
{f'- Description: {trip.description}' if trip.description else ''}

**Your Role:** {role_type.title()}
{get_role_description(role_type)}

**Join the trip:**
Click here to view trip details and RSVP:
{invitation_url}

If you don't have an account yet, you can quickly register.

Looking forward to having you join us!

---
GroupTrips
"""
    
    return {
        'subject': subject,
        'body': body
    }


def send_email_invitation(trip: Trip, sender: User, recipient_email: str, role_type: str) -> bool:
    """Send email invitation for a trip.
    
    Args:
        trip (Trip): Trip to invite to
        sender (User): User sending the invitation
        recipient_email (str): Email address to send to
        role_type (str): The role for the invitee
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        invitation_code = secrets.token_urlsafe(16)
        expires_at = datetime.utcnow() + timedelta(days=7)

        email_content = create_invitation_email_content(trip, sender, invitation_code, role_type)
        
        success = send_email(
            to_email=recipient_email,
            subject=email_content['subject'],
            body=email_content['body'],
            email_type='invitation',
            user_id=sender.id
        )
        
        if success:
            invitation = TripInvitation(
                trip_id=trip.id,
                invitation_code=invitation_code,
                role_type=role_type,
                created_by=sender.id,
                expires_at=expires_at
            )
            db.session.add(invitation)
            db.session.commit()
            return True
        else:
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error sending email invitation: {str(e)}")
        return False


def send_bulk_invitations(trip: Trip, sender: User, emails: List[str], role_type: str) -> Dict[str, Any]:
    """Send bulk invitations via email.
    
    Args:
        trip (Trip): Trip to invite to
        sender (User): User sending the invitations
        emails (List[str]): List of email addresses
        role_type (str): The role for the invitees
        
    Returns:
        Dict[str, Any]: Results summary
    """
    results = {
        'email_sent': 0,
        'email_failed': 0,
        'errors': []
    }
    
    for email in emails:
        if validate_email(email):
            if send_email_invitation(trip, sender, email, role_type):
                results['email_sent'] += 1
            else:
                results['email_failed'] += 1
                results['errors'].append(f"Failed to send email to {email}")
        else:
            results['email_failed'] += 1
            results['errors'].append(f"Invalid email format: {email}")
    
    return results
