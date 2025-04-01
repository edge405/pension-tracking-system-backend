import os
from werkzeug.utils import secure_filename
import uuid

def upload_image(file, upload_folder='static/uploads'):
    """
    Simple function to upload and save an image file
    
    Args:
        file: The file object from request.files
        upload_folder: Directory where images will be stored
        
    Returns:
        str: Path to the saved image or None if upload failed
    """
    # Check if the file exists and has an allowed extension
    if not file or file.filename == '':
        return None
        
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if '.' not in file.filename:
        return None
        
    extension = file.filename.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions:
        return None
    
    # Create upload directory if it doesn't exist
    os.makedirs(upload_folder, exist_ok=True)
    
    # Create a unique filename
    filename = secure_filename(f"{uuid.uuid4().hex}.{extension}")
    
    # Save the file
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    return file_path