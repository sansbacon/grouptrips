"""Timezone utilities for the Over-Under Contests application."""
from datetime import datetime
import pytz
from flask import request


# Common timezones for the dropdown
COMMON_TIMEZONES = [
    ('US/Eastern', 'Eastern Time (US/Eastern)'),
    ('US/Central', 'Central Time (US/Central)'),
    ('US/Mountain', 'Mountain Time (US/Mountain)'),
    ('US/Pacific', 'Pacific Time (US/Pacific)'),
    ('US/Alaska', 'Alaska Time (US/Alaska)'),
    ('US/Hawaii', 'Hawaii Time (US/Hawaii)'),
    ('UTC', 'UTC'),
    ('Europe/London', 'London (Europe/London)'),
    ('Europe/Paris', 'Paris (Europe/Paris)'),
    ('Europe/Berlin', 'Berlin (Europe/Berlin)'),
    ('Europe/Rome', 'Rome (Europe/Rome)'),
    ('Europe/Madrid', 'Madrid (Europe/Madrid)'),
    ('Asia/Tokyo', 'Tokyo (Asia/Tokyo)'),
    ('Asia/Shanghai', 'Shanghai (Asia/Shanghai)'),
    ('Asia/Kolkata', 'Mumbai/Delhi (Asia/Kolkata)'),
    ('Australia/Sydney', 'Sydney (Australia/Sydney)'),
    ('Australia/Melbourne', 'Melbourne (Australia/Melbourne)'),
]


def get_user_timezone():
    """Get user's timezone from session or default to US/Central.
    
    Returns:
        str: Timezone string
    """
    # In a real application, you might store this in user preferences
    # For now, we'll use a default or try to detect from browser
    return 'US/Central'


def convert_to_utc(local_datetime, timezone_str):
    """Convert local datetime to UTC.
    
    Args:
        local_datetime (datetime): Local datetime (naive)
        timezone_str (str): Timezone string (e.g., 'US/Central')
        
    Returns:
        datetime: UTC datetime
    """
    if local_datetime is None:
        return None
    
    try:
        # Get the timezone
        tz = pytz.timezone(timezone_str)
        
        # Localize the naive datetime to the specified timezone
        localized_dt = tz.localize(local_datetime)
        
        # Convert to UTC
        utc_dt = localized_dt.astimezone(pytz.UTC)
        
        # Return as naive UTC datetime (since SQLAlchemy stores as naive)
        return utc_dt.replace(tzinfo=None)
    except Exception as e:
        # If there's an error, assume the datetime is already UTC
        return local_datetime


def convert_from_utc(utc_datetime, timezone_str):
    """Convert UTC datetime to local timezone.
    
    Args:
        utc_datetime (datetime): UTC datetime (naive)
        timezone_str (str): Target timezone string
        
    Returns:
        datetime: Local datetime (naive)
    """
    if utc_datetime is None:
        return None
    
    try:
        # Treat the input as UTC
        utc_tz = pytz.UTC
        utc_dt = utc_tz.localize(utc_datetime)
        
        # Convert to target timezone
        target_tz = pytz.timezone(timezone_str)
        local_dt = utc_dt.astimezone(target_tz)
        
        # Return as naive datetime
        return local_dt.replace(tzinfo=None)
    except Exception as e:
        # If there's an error, return the original datetime
        return utc_datetime


def format_datetime_with_timezone(utc_datetime, timezone_str, format_str='%Y-%m-%d %H:%M'):
    """Format UTC datetime in the specified timezone.
    
    Args:
        utc_datetime (datetime): UTC datetime
        timezone_str (str): Target timezone string
        format_str (str): Format string
        
    Returns:
        str: Formatted datetime string
    """
    if utc_datetime is None:
        return 'Not set'
    
    local_dt = convert_from_utc(utc_datetime, timezone_str)
    if local_dt:
        tz_name = timezone_str.split('/')[-1] if '/' in timezone_str else timezone_str
        return f"{local_dt.strftime(format_str)} ({tz_name})"
    return utc_datetime.strftime(format_str)


def get_timezone_choices():
    """Get timezone choices for form dropdown.
    
    Returns:
        list: List of (value, label) tuples
    """
    return COMMON_TIMEZONES
