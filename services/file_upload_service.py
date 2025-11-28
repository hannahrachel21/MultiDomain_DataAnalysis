import os
import uuid
from fastapi import UploadFile
from config import UPLOAD_DIR
from services.session_service import get_session_by_file_name

def save_uploaded_file(file: UploadFile) -> str:
    """
    Save the uploaded Excel file ONLY IF it does not already exist.
    If the file exists (same filename), reuse existing file_path.
    """
    ext = os.path.splitext(file.filename)[1]
    if ext.lower() not in [".xlsx", ".xls"]:
        raise ValueError("Only Excel files (.xlsx, .xls) are supported.")

    # Check DB if this filename was uploaded before
    existing_session = get_session_by_file_name(file.filename)

    if existing_session:
        # File already exists in UPLOAD_DIR → Skip saving duplicate file
        if os.path.exists(existing_session.file_path):
            return existing_session.file_path

    #Save new file
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return file_path
