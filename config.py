import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import pytz

load_dotenv()

class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    REQUIRED_ROLE = os.getenv("REQUIRED_ROLE", "FileUploader")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    MINIO_BUCKET = "fileshare01"
    MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
    VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
    CLAMAV_HOST = os.getenv("CLAMAV_HOST", "clamav")
    CLAMAV_PORT = os.getenv("CLAMAV_PORT", "3310")
    CLAMAV_TIMEOUT = int(os.getenv("CLAMAV_TIMEOUT", "300"))
    SERVICE_URL = os.getenv("SERVICE_URL", "http://localhost:8000")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "5368709120"))
    URL_EXPIRY_DAYS = int(os.getenv("URL_EXPIRY_DAYS", "3"))
    TIMEZONE = os.getenv("TIMEZONE", "UTC")
    APP_LANGUAGE = os.getenv("APP_LANGUAGE", "en")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    SCAN_LOG_DB_PATH = os.getenv("SCAN_LOG_DB_PATH", "db/scan_logs.db")
    SCAN_LOG_RETENTION_DAYS = int(os.getenv("SCAN_LOG_RETENTION_DAYS", "365"))
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(',')
    ALLOW_PENDING_DOWNLOAD = os.getenv("ALLOW_PENDING_DOWNLOAD", "false").lower() == "true"
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "10"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.zip', '.jpg', '.jpeg', '.png',
                         '.mp4', '.avi', '.mov', '.mkv', '.webm',
                         '.txt', '.csv', '.json', '.xml'}
    ALLOWED_MIMES = {
        'application/pdf',
        'image/jpeg',
        'image/png',
        'application/zip',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'video/mp4',
        'video/x-msvideo',
        'video/quicktime',
        'video/x-matroska',
        'video/webm',
        'text/plain',
        'text/csv',
        'application/json',
        'text/xml'
    }
    SUPPORTED_LANGUAGES = {'en', 'ja'}
    
    @classmethod
    def get_timezone(cls):
        try:
            return pytz.timezone(cls.TIMEZONE)
        except pytz.exceptions.UnknownTimeZoneError:
            logger = logging.getLogger(__name__)
            logger.warning(f"Unknown timezone '{cls.TIMEZONE}'. Falling back to UTC.")
            return pytz.UTC

    @classmethod
    def validate(cls):
        errors = []
        warnings = []

        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN is not set")

        if not cls.MINIO_ACCESS_KEY or not cls.MINIO_SECRET_KEY:
            errors.append("MinIO credentials are not set")

        if not cls.MINIO_ENDPOINT:
            errors.append("MINIO_ENDPOINT is not set")

        if cls.MAX_FILE_SIZE > 10 * 1024 * 1024 * 1024:
            errors.append("MAX_FILE_SIZE is too large (>10GB)")

        if cls.MAX_FILE_SIZE < 1024:
            errors.append("MAX_FILE_SIZE is too small (<1KB)")

        try:
            pytz.timezone(cls.TIMEZONE)
        except pytz.exceptions.UnknownTimeZoneError:
            errors.append(f"Invalid TIMEZONE: {cls.TIMEZONE}")

        if cls.APP_LANGUAGE not in cls.SUPPORTED_LANGUAGES:
            warnings.append(f"Unsupported APP_LANGUAGE: {cls.APP_LANGUAGE}. Supported: {', '.join(cls.SUPPORTED_LANGUAGES)}")

        if cls.SECRET_KEY == "change-this-in-production":
            warnings.append("SECRET_KEY is using default value. Please change in production.")

        if not (1 <= cls.API_PORT <= 65535):
            errors.append(f"Invalid API_PORT: {cls.API_PORT}")

        if cls.URL_EXPIRY_DAYS < 1:
            errors.append("URL_EXPIRY_DAYS must be at least 1")

        if cls.URL_EXPIRY_DAYS > 365:
            warnings.append(f"URL_EXPIRY_DAYS is very large: {cls.URL_EXPIRY_DAYS} days")

        logger = logging.getLogger(__name__)
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        return True

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger