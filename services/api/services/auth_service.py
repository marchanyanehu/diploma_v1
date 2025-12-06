"""
Authentication service encapsulating hashing and token operations.

Keeps FastAPI routes focused on transport concerns and uses a repository
abstraction for user lookup to honor DIP.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..db_models import User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MAX_BCRYPT_PASSWORD_BYTES = 72
PASSWORD_BYTES_ERROR = (
    "Password must be at most 72 bytes when encoded as UTF-8 to work with bcrypt."
)


class UserRepository(Protocol):
    """Minimal contract for user lookup."""

    def get_by_username(self, username: str) -> Optional[User]:
        ...


class AuthService:
    """Auth operations with injected repository and settings."""

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int,
        user_repo: UserRepository,
        pwd_context: Optional[CryptContext] = None,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.user_repo = user_repo
        self.pwd_context = pwd_context or CryptContext(schemes=["bcrypt"], deprecated="auto")

    # ----- Password utilities -----
    def _ensure_password_within_limit(self, password: str) -> None:
        if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
            raise ValueError(PASSWORD_BYTES_ERROR)

    def hash_password(self, password: str) -> str:
        self._ensure_password_within_limit(password)
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    # ----- JWT utilities -----
    def create_access_token(self, username: str, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = {"sub": username}
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_username(self, token: str) -> str:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        username: Optional[str] = payload.get("sub")
        if not username:
            raise JWTError("Token missing subject")
        return username

    # ----- User resolution -----
    def get_user(self, username: str) -> Optional[User]:
        return self.user_repo.get_by_username(username)


class SqlAlchemyUserRepository(UserRepository):
    """User repository backed by SQLAlchemy session."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

