
from datetime import timedelta
from typing import Optional
from shared.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from shared.database import get_db, User
from .services.auth_service import (
    AuthService,
    SqlAlchemyUserRepository,
    MAX_BCRYPT_PASSWORD_BYTES,
    PASSWORD_BYTES_ERROR,
)

# Config defaults sourced from settings
SECRET_KEY = settings.secret_key
ALGORITHM = getattr(settings, "jwt_algorithm", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = getattr(settings, "access_token_expire_minutes", 30)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Provide AuthService with DB-backed user repository."""
    repo = SqlAlchemyUserRepository(db)
    return AuthService(
        secret_key=SECRET_KEY,
        algorithm=ALGORITHM,
        access_token_expire_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        user_repo=repo,
    )


def get_password_hash(password: str, auth_service: AuthService = Depends(get_auth_service)) -> str:
    return auth_service.hash_password(password)


def verify_password(plain_password: str, hashed_password: str, auth_service: AuthService = Depends(get_auth_service)) -> bool:
    return auth_service.verify_password(plain_password, hashed_password)


def create_access_token(username: str, expires_delta: Optional[timedelta] = None, auth_service: AuthService = Depends(get_auth_service)) -> str:
    return auth_service.create_access_token(username, expires_delta)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        username = auth_service.decode_username(token)
    except JWTError:
        raise credentials_exception

    user = auth_service.get_user(username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
