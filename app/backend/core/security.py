from fastapi import Depends


def get_current_user() -> dict:
    """Placeholder for Google OAuth."""
    return {"sub": "anonymous"}
