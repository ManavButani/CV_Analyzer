from passlib.context import CryptContext
import traceback
import sys


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def get_traceback_string() -> str:
    """Get formatted traceback string for current exception"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_traceback:
        return "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    return ""
