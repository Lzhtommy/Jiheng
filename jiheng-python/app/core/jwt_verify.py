import jwt
from fastapi import HTTPException, Request, status

from app.config import settings


async def verify_jwt(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_TOKEN_MISSING")
    token = auth_header[7:]
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_TOKEN_INVALID")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_TOKEN_INVALID")
    if "sub" not in payload and "user_id" in payload:
        payload["sub"] = str(payload["user_id"])
    return payload
