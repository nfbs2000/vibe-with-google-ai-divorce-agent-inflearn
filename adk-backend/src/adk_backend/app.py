from __future__ import annotations

import asyncio
import json
import time
import os
import signal
import sys
import logging
from typing import Any, AsyncIterator, Dict, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# ⚠️ IMPORTANT: .env 파일을 먼저 로드해야 다른 모듈의 config가 환경 변수를 읽을 수 있습니다
# 환경 변수 로드 (프로젝트 루트의 .env 파일)
# adk-backend/src/adk_backend/app.py에서 ../../../.env로 접근
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

# .env 로드 후 다른 모듈 import
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from .config import get_settings
from .live import LiveRunManager, format_sse_message
from .tools.bigquery import bigquery_list_templates, bigquery_render_template
from .sessions import ensure_session
from .workflows.divorce import get_runner
from .nlp.gemini_client import initialize_gemini_client_with_cag

# API 라우터 import
from .api import chat, data, system

# 로깅 설정 import
from .utils.logging_config import setup_logging
from .middleware.logging_middleware import RequestLoggingMiddleware

# 로깅 초기화
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(level=log_level, enable_colors=True)
logger = logging.getLogger(__name__)


# Signal handler for graceful shutdown
def handle_shutdown_signal(signum, frame):
    """Ctrl+C (SIGINT) 및 SIGTERM 신호를 깔끔하게 처리"""
    logger.info("\n" + "="*80)
    logger.info("🛑 Shutdown signal received. Cleaning up...")
    logger.info("="*80)
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, handle_shutdown_signal)
signal.signal(signal.SIGTERM, handle_shutdown_signal)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 시 실행되는 이벤트"""
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 Unified Divorce Intelligence Platform Starting...")
    settings = get_settings()
    logger.info(f"📊 Project: {settings.google_project_id}")
    logger.info(f"📝 Log Level: {log_level}")
    logger.info("=" * 80)

    # 1. CAG 메타데이터 로드 및 Gemini 클라이언트 초기화
    logger.info("📚 CAG (Context-Augmented Generation) 초기화 중...")
    try:
        initialize_gemini_client_with_cag()
        logger.info("✅ CAG 초기화 완료 - 모든 사용자가 Context Cache를 공유합니다")
    except Exception as e:
        logger.error(f"❌ CAG 초기화 실패: {str(e)}")

    yield

    # Shutdown
    logger.info("=" * 80)
    logger.info("👋 Unified Divorce Intelligence Platform Shutting down...")
    logger.info("=" * 80)


app = FastAPI(
    title="Unified Divorce Intelligence Platform",
    description="Gemini 멀티모달 AI와 BigQuery 기반의 통합 이혼 솔루션 플랫폼",
    version="1.0.0",
    lifespan=lifespan
)
settings = get_settings()
live_manager = LiveRunManager()

# CORS 설정
origins = [
    "http://localhost:3000",  # React 개발 서버
    "http://localhost:5173",  # Vite 개발 서버
    "http://localhost:8005",  # Frontend 서버
    "http://localhost:8006",  # AI Phishing Frontend
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8005",
    "http://127.0.0.1:8006",
]

# 환경 변수에서 추가 origins 로드
if os.getenv('CORS_ORIGINS'):
    additional_origins = os.getenv('CORS_ORIGINS').split(',')
    origins.extend([origin.strip() for origin in additional_origins])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 미들웨어 등록
app.add_middleware(RequestLoggingMiddleware)

# 정적 파일 서빙 설정 (업로드된 파일 접근용)
# 주의: 프로덕션 환경에서는 Nginx/Apache 등을 사용하는 것이 권장됨
upload_dir = os.path.join(os.getcwd(), "data", "uploads")
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# API 라우터 등록
app.include_router(chat.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(system.router, prefix="/api")


class RunRequest(BaseModel):
    prompt: str = Field(..., description="사용자 질문")
    user_id: Optional[str] = None
    session_id: Optional[str] = None


def _serialize_event(event: Any) -> Dict[str, Any]:
    try:
        payload = event.model_dump(by_alias=True, exclude_none=True)
    except AttributeError:  # pragma: no cover - defensive
        payload = json.loads(json.dumps(event, default=str))
    payload["_meta"] = {"timestamp": time.time()}
    return payload


async def _run_once(request: RunRequest) -> Dict[str, Any]:
    runner = get_runner()
    session = await ensure_session(request.user_id, request.session_id)
    message = genai_types.Content(role="user", parts=[genai_types.Part(text=request.prompt)])
    events = []
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=message,
    ):
        events.append(_serialize_event(event))
    return {"session_id": session.id, "events": events}


# 기본 라우트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Unified Divorce Intelligence API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/system/health"
    }

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "project": settings.google_project_id}

# 레거시 헬스체크 엔드포인트 (하위 호환성)
@app.get("/api/health")
async def legacy_health_check():
    """레거시 헬스체크 엔드포인트 (리다이렉트)"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0",
        "message": "Use /api/system/health for detailed health information"
    }


@app.post("/api/run")
async def run(request: RunRequest) -> JSONResponse:
    if not request.prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    result = await _run_once(request)
    return JSONResponse(result)


class LiveRunRequest(BaseModel):
    prompt: str = Field(..., description="사용자 질문")
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class LiveRunResponse(BaseModel):
    run_id: str
    session_id: str


@app.post("/api/live/run", response_model=LiveRunResponse)
async def live_run(request: LiveRunRequest) -> LiveRunResponse:
    if not request.prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    run_id, session_id = await live_manager.start_run(
        prompt=request.prompt,
        user_id=request.user_id,
        session_id=request.session_id,
    )
    return LiveRunResponse(run_id=run_id, session_id=session_id)


@app.get("/api/live/events")
async def stream_events(run_id: str, request: Request):
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required")
    try:
        queue = await live_manager.subscribe(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def event_generator() -> AsyncIterator[str]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield format_sse_message(message)
                except asyncio.TimeoutError:
                    yield "event: keepalive\ndata: {}\n\n"
        finally:
            await live_manager.unsubscribe(run_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/templates")
async def list_templates() -> Dict[str, Any]:
    """사용 가능한 BigQuery 템플릿 목록을 반환."""
    result_json = bigquery_list_templates()
    return json.loads(result_json)


class RenderTemplateRequest(BaseModel):
    template_id: str = Field(..., description="템플릿 ID")
    params: Optional[Dict[str, Any]] = Field(default=None, description="템플릿 파라미터")
    dry_run: bool = False
    project_id: Optional[str] = None


@app.post("/api/templates/render")
async def render_template(request: RenderTemplateRequest) -> Dict[str, Any]:
    """BigQuery 템플릿을 렌더링."""
    params_json = json.dumps(request.params) if request.params else None
    result_json = bigquery_render_template(
        template_id=request.template_id,
        params_json=params_json,
        dry_run=request.dry_run,
        project_id=request.project_id,
    )
    return json.loads(result_json)
