"""
API 요청/응답 로깅 미들웨어
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..utils.logging_config import get_api_logger

logger = logging.getLogger(__name__)
api_logger = get_api_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    모든 API 요청/응답을 로깅하는 미들웨어
    """

    def __init__(self, app: ASGIApp, skip_paths: list[str] = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health", "/docs", "/openapi.json", "/redoc"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)

        # 요청 시작 시간
        start_time = time.time()

        # 요청 정보 로깅
        logger.debug(
            f"→ Request: {request.method} {request.url.path} "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        # 요청 본문 로깅 (POST/PUT/PATCH만)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body and len(body) < 1000:  # 1KB 미만만 로깅
                    logger.debug(f"  Body preview: {body.decode()[:200]}...")
            except Exception as e:
                logger.debug(f"  Could not read body: {e}")

        # 응답 처리
        try:
            response = await call_next(request)
            status_code = response.status_code

            # 응답 시간 계산
            duration_ms = (time.time() - start_time) * 1000

            # API 로거로 요청/응답 요약 로깅
            api_logger.info(
                "",  # 메시지는 RequestLogFormatter에서 처리
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                }
            )

            # 에러 응답 상세 로깅
            if status_code >= 400:
                logger.warning(
                    f"← Response: {status_code} in {duration_ms:.0f}ms "
                    f"Path: {request.url.path}"
                )
            elif duration_ms > 1000:
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {duration_ms:.0f}ms"
                )

            return response

        except Exception as e:
            # 예외 발생 시 로깅
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                f"✖ Request failed: {request.method} {request.url.path} "
                f"Error: {str(e)[:100]}"
            )

            api_logger.error(
                "",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                }
            )

            raise
