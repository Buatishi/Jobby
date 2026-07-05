from typing import Annotated, Any, cast

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.database import get_supabase_client
from app.models.auth import CurrentUser

bearer_scheme = HTTPBearer(auto_error=False)
_jwks_cache: dict[str, Any] | None = None


async def fetch_jwks(settings: Settings) -> dict[str, Any]:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.supabase_jwks_url)
        response.raise_for_status()
        jwks = cast(dict[str, Any], response.json())

    _jwks_cache = jwks
    return jwks


def _unauthorized(message: str = "Token inválido") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": message, "code": "UNAUTHORIZED", "details": {}},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _select_signing_key(token: str, jwks: dict[str, Any]) -> tuple[Any, str]:
    header = jwt.get_unverified_header(token)
    key_id = header.get("kid")

    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == key_id:
            algorithm = key_data.get("alg")
            if algorithm not in {"RS256", "ES256"}:
                raise _unauthorized()
            return jwt.PyJWK(key_data).key, str(algorithm)

    raise _unauthorized()


def _token_algorithm(token: str) -> str:
    algorithm = jwt.get_unverified_header(token).get("alg")
    if not isinstance(algorithm, str):
        raise _unauthorized()
    return algorithm


def _decode_token(
    token: str,
    signing_key: Any,
    algorithm: str,
    *,
    verify_audience: bool = True,
) -> dict[str, Any]:
    options = {"verify_exp": True}
    if not verify_audience:
        options["verify_aud"] = False

    kwargs: dict[str, Any] = {
        "key": signing_key,
        "algorithms": [algorithm],
        "options": options,
    }
    if verify_audience:
        kwargs["audience"] = "authenticated"

    return jwt.decode(token, **kwargs)


async def validate_jwt(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    if credentials is None:
        raise _unauthorized("Token requerido")

    try:
        token = credentials.credentials
        algorithm = _token_algorithm(token)
        if algorithm == "HS256":
            if not settings.supabase_jwt_secret:
                raise _unauthorized()
            signing_key = settings.supabase_jwt_secret
        else:
            jwks = await fetch_jwks(settings)
            signing_key, algorithm = _select_signing_key(token, jwks)

        return _decode_token(token, signing_key, algorithm)
    except HTTPException:
        raise
    except jwt.InvalidAudienceError:
        try:
            return _decode_token(
                token,
                signing_key,
                algorithm,
                verify_audience=False,
            )
        except jwt.PyJWTError as exc:
            raise _unauthorized() from exc
    except (jwt.PyJWTError, httpx.HTTPError, KeyError, ValueError) as exc:
        raise _unauthorized() from exc


async def get_current_user(
    claims: Annotated[dict[str, Any], Depends(validate_jwt)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> CurrentUser:
    supabase_uid = claims.get("sub")
    if not isinstance(supabase_uid, str) or not supabase_uid:
        raise _unauthorized()

    response = (
        await supabase.table("users")
        .select("id,supabase_uid,email")
        .eq("supabase_uid", supabase_uid)
        .single()
        .execute()
    )
    user_data = getattr(response, "data", None)
    if not isinstance(user_data, dict):
        raise _unauthorized("Usuario no encontrado")

    return CurrentUser(
        id=str(user_data["id"]),
        supabase_uid=str(user_data["supabase_uid"]),
        email=user_data.get("email"),
    )
