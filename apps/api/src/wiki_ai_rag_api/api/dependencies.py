import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request, status

from wiki_ai_rag_api.core.config import get_settings

_request_windows: dict[str, deque[float]] = defaultdict(deque)


async def require_admin(x_admin_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.auth_enabled:
        return

    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin API key is not configured",
        )

    if not x_admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key is required",
        )

    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )


async def require_user_or_admin(
    x_user_api_key: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.auth_enabled:
        return

    if x_admin_api_key and settings.admin_api_key and x_admin_api_key == settings.admin_api_key:
        return

    if not settings.user_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User API key is not configured",
        )

    if not x_user_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User API key is required",
        )

    if x_user_api_key != settings.user_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user API key",
        )


async def enforce_question_rate_limit(request: Request) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return

    client_host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _request_windows[client_host]
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
