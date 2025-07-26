import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder=''):
    """
    Save an uploaded file to the uploads directory.
    
    Args:
        file: The uploaded file object
        subfolder: Optional subfolder within uploads directory
        
    Returns:
        str: The relative path to the saved file, or None if save failed
    """
    if file and file.filename and allowed_file(file.filename):
        # Generate a unique filename to prevent conflicts
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Create the full upload path
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, unique_filename)
        
        try:
            file.save(file_path)
            # Return the relative path from the static directory
            return os.path.join('uploads', subfolder, unique_filename).replace('\\', '/')
        except Exception as e:
            current_app.logger.error(f"Error saving file: {str(e)}")
            return None
    
    return None

def delete_file(file_path):
    """
    Delete a file from the uploads directory.
    
    Args:
        file_path: The relative path to the file (from static directory)
    """
    if file_path:
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path.replace('uploads/', ''))
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
        except Exception as e:
            current_app.logger.error(f"Error deleting file: {str(e)}")
    
    return False
