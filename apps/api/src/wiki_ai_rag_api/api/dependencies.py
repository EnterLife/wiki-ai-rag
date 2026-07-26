import time
from collections import defaultdict, deque
from functools import lru_cache
from secrets import compare_digest

from fastapi import Depends, Header, HTTPException, Request, status

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.access import AccessContext, remember_access_context

_request_windows: dict[str, deque[float]] = defaultdict(deque)


async def get_current_principal(
    authorization: str | None = Header(default=None),
    x_user_api_key: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None),
) -> AccessContext:
    settings = get_settings()
    if not settings.auth_enabled:
        return remember_access_context(AccessContext.system())

    if settings.auth_provider == "oidc":
        return remember_access_context(_oidc_principal(authorization))
    if settings.auth_provider != "api_key":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication provider is not configured correctly",
        )

    if (
        x_admin_api_key
        and settings.admin_api_key
        and compare_digest(x_admin_api_key, settings.admin_api_key)
    ):
        return remember_access_context(
            AccessContext(subject="api-key-admin", is_admin=True)
        )

    if (
        x_user_api_key
        and settings.user_api_key
        and compare_digest(x_user_api_key, settings.user_api_key)
    ):
        return remember_access_context(
            AccessContext(
                subject=settings.user_api_key_subject,
                groups=frozenset(settings.user_api_key_groups),
            )
        )

    if not x_user_api_key and not x_admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )


async def require_admin(
    principal: AccessContext = Depends(get_current_principal),
) -> AccessContext:
    settings = get_settings()
    if not settings.auth_enabled:
        return principal

    if not settings.admin_api_key:
        if settings.auth_provider == "api_key":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin API key is not configured",
            )
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role is required",
        )
    return principal


async def require_user_or_admin(
    principal: AccessContext = Depends(get_current_principal),
) -> AccessContext:
    return principal


async def enforce_question_rate_limit(
    request: Request,
    principal: AccessContext = Depends(require_user_or_admin),
) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return

    client_host = request.client.host if request.client else "unknown"
    rate_limit_key = principal.subject if settings.auth_enabled else client_host
    now = time.monotonic()
    window = _request_windows[rate_limit_key]
    while window and now - window[0] >= 60:
        window.popleft()

    if len(window) >= settings.question_rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Question rate limit exceeded",
        )

    window.append(now)


def reset_rate_limiter() -> None:
    _request_windows.clear()


def _oidc_principal(authorization: str | None) -> AccessContext:
    settings = get_settings()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required",
        )
    if not settings.oidc_issuer or not settings.oidc_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OIDC issuer and JWKS URL must be configured",
        )

    import jwt

    token = authorization.removeprefix("Bearer ").strip()
    try:
        signing_key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"verify_aud": settings.oidc_audience is not None},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        ) from exc

    subject = str(claims.get("sub") or "")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token has no subject",
        )
    raw_groups = claims.get(settings.oidc_groups_claim, [])
    if isinstance(raw_groups, str):
        raw_groups = [raw_groups]
    groups = frozenset(str(group) for group in raw_groups)
    return AccessContext(
        subject=subject,
        groups=groups,
        is_admin=settings.oidc_admin_group in groups,
    )


@lru_cache
def _jwks_client(jwks_url: str):
    import jwt

    return jwt.PyJWKClient(jwks_url)
