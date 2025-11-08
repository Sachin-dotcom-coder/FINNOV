import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # uploads
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads"))
    ALLOWED_EXTENSIONS = {"txt", "pdf", "docx", "csv", "json", "png", "jpg", "jpeg"}

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
