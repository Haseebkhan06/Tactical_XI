
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import InvalidTokenError
from pydantic import BaseModel

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))

ADMIN_USERNAME = os.getenv("TACTICAL_ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("TACTICAL_ADMIN_PASSWORD", "")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def validate_auth_configuration() -> None:
    """Fail closed if authentication has not been configured safely."""
    if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must be configured with a long random secret in .env"
        )

    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise RuntimeError(
            "TACTICAL_ADMIN_USERNAME and TACTICAL_ADMIN_PASSWORD must be set in .env"
        )

    if JWT_ALGORITHM != "HS256":
        raise RuntimeError("This implementation supports HS256 only.")

    if JWT_EXPIRE_MINUTES < 1:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be at least 1.")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUser(BaseModel):
    username: str
    role: str


def authenticate_user(username: str, password: str) -> bool:
    """Validate the configured development/admin account."""
    username_ok = hmac.compare_digest(
        username.encode("utf-8"),
        ADMIN_USERNAME.encode("utf-8"),
    )
    password_ok = hmac.compare_digest(
        password.encode("utf-8"),
        ADMIN_PASSWORD.encode("utf-8"),
    )
    return username_ok and password_ok


def create_access_token(username: str) -> tuple[str, int]:
    validate_auth_configuration()

    expires_in = JWT_EXPIRE_MINUTES * 60
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in)

    payload: dict[str, Any] = {
        "sub": username,
        "role": "admin",
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    return token, expires_in


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> CurrentUser:
    """Verify the bearer token before allowing access to protected routes."""
    try:
        validate_auth_configuration()

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )

        username = payload.get("sub")
        role = payload.get("role")

        if not isinstance(username, str) or not username:
            raise InvalidTokenError("Missing subject")

        if not isinstance(role, str) or not role:
            raise InvalidTokenError("Missing role")

        return CurrentUser(username=username, role=role)

    except (InvalidTokenError, RuntimeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    validate_auth_configuration()

    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, expires_in = create_access_token(form_data.username)

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
    )


@router.get("/me", response_model=CurrentUser)
async def read_current_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    return current_user


@router.get("/protected-check")
async def protected_check(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    return {
        "message": "Authentication successful",
        "username": current_user.username,
        "role": current_user.role,
    }
