import asyncio
import uuid
from typing import Annotated, Any, cast

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.database import get_supabase_client
from app.models.auth import CurrentUser

bearer_scheme = HTTPBearer(auto_error=False)
# Marca de las claims que validó Supabase Auth por HTTP: ese camino ya rechaza los
# tokens de sesiones cerradas, así que no hace falta volver a consultar la sesión.
SESSION_VERIFIED_BY_AUTH = "x-jobby-session-verified"
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


async def _validate_with_supabase_auth(
    token: str,
    settings: Settings,
) -> dict[str, Any]:
    if not settings.supabase_anon_key:
        raise _unauthorized()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            settings.supabase_auth_user_url,
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.supabase_anon_key,
            },
        )

    if response.status_code != status.HTTP_200_OK:
        raise _unauthorized()

    user_payload = response.json()
    supabase_uid = user_payload.get("id")
    if not isinstance(supabase_uid, str) or not supabase_uid:
        raise _unauthorized()

    return {
        "sub": supabase_uid,
        "email": user_payload.get("email"),
        "aud": "authenticated",
        SESSION_VERIFIED_BY_AUTH: True,
    }


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


def _claim_email(claims: dict[str, Any]) -> str | None:
    email = claims.get("email")
    return email if isinstance(email, str) and email else None


def _claim_full_name(claims: dict[str, Any]) -> str | None:
    metadata = claims.get("user_metadata")
    if not isinstance(metadata, dict):
        metadata = claims.get("raw_user_meta_data")
    if not isinstance(metadata, dict):
        return None

    full_name = metadata.get("full_name") or metadata.get("name")
    return full_name if isinstance(full_name, str) and full_name else None


async def validate_jwt(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    if credentials is None:
        raise _unauthorized("Token requerido")

    token = credentials.credentials

    try:
        algorithm = _token_algorithm(token)
        if algorithm == "HS256":
            if not settings.supabase_jwt_secret:
                raise _unauthorized()
            signing_key = settings.supabase_jwt_secret
        else:
            jwks = await fetch_jwks(settings)
            signing_key, algorithm = _select_signing_key(token, jwks)

        return _decode_token(token, signing_key, algorithm)
    except jwt.InvalidAudienceError:
        try:
            return _decode_token(
                token,
                signing_key,
                algorithm,
                verify_audience=False,
            )
        except jwt.PyJWTError:
            return await _validate_with_supabase_auth(token, settings)
    except HTTPException as exc:
        detail = exc.detail
        if isinstance(detail, dict) and detail.get("error") == "Token requerido":
            raise
        return await _validate_with_supabase_auth(token, settings)
    except (jwt.PyJWTError, httpx.HTTPError, KeyError, ValueError):
        return await _validate_with_supabase_auth(token, settings)


async def _session_is_active(
    supabase: Any, session_id: Any, supabase_uid: str
) -> bool:
    """Si la sesión del token sigue abierta en Supabase Auth (migración 027).

    La firma y el vencimiento se validan localmente; esto agrega lo que la firma no
    puede saber: que la persona cerró sesión. Cerrarla borra la sesión y el token deja
    de servir.
    """
    try:
        session_uuid = uuid.UUID(str(session_id))
    except ValueError:
        return False
    response = await supabase.rpc(
        "session_is_active",
        {"p_session_id": str(session_uuid), "p_supabase_uid": supabase_uid},
    ).execute()
    return getattr(response, "data", None) is True


async def get_current_user(
    claims: Annotated[dict[str, Any], Depends(validate_jwt)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> CurrentUser:
    supabase_uid = claims.get("sub")
    if not isinstance(supabase_uid, str) or not supabase_uid:
        raise _unauthorized()

    async def fetch_user() -> Any:
        response = (
            await supabase.table("users")
            .select("id,supabase_uid,email,role,tier")
            .eq("supabase_uid", supabase_uid)
            .maybe_single()
            .execute()
        )
        return getattr(response, "data", None)

    if claims.get(SESSION_VERIFIED_BY_AUTH):
        user_data = await fetch_user()
    else:
        # En paralelo con la lectura del usuario: no suma otra ida y vuelta.
        session_active, user_data = await asyncio.gather(
            _session_is_active(supabase, claims.get("session_id"), supabase_uid),
            fetch_user(),
        )
        if not session_active:
            raise _unauthorized("La sesión se cerró. Volvé a iniciar sesión.")

    if not isinstance(user_data, dict):
        email = _claim_email(claims)
        if email is None:
            raise _unauthorized("Email no encontrado en token")

        insert_response = (
            await supabase.table("users")
            .insert(
                {
                    "supabase_uid": supabase_uid,
                    "email": email,
                    "full_name": _claim_full_name(claims),
                }
            )
            .execute()
        )
        inserted_data = getattr(insert_response, "data", None)
        if isinstance(inserted_data, list) and inserted_data:
            user_data = inserted_data[0]
        elif isinstance(inserted_data, dict):
            user_data = inserted_data
        else:
            retry_response = (
                await supabase.table("users")
                .select("id,supabase_uid,email,role,tier")
                .eq("supabase_uid", supabase_uid)
                .maybe_single()
                .execute()
            )
            user_data = getattr(retry_response, "data", None)

    if not isinstance(user_data, dict):
        raise _unauthorized("Usuario no encontrado")

    # El perfil maestro lo crea la base al insertar en users (migración 028).
    return CurrentUser(
        id=str(user_data["id"]),
        supabase_uid=str(user_data["supabase_uid"]),
        email=user_data.get("email"),
        role=str(user_data.get("role") or "user"),
        tier=str(user_data.get("tier") or "free"),
    )
