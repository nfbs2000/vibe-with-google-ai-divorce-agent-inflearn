#!/usr/bin/env python3
"""
채팅 관련 API 라우터
"""

import logging
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from .schemas.chat import (
    QueryRequest, QueryResponse, AgentSummary, ExampleQuery, 
    UploadResponse, FeedbackRequest, FeedbackResponse, HistoryResponse
)
from ..services.chat_service import (
    process_query_service, 
    stream_adk_events_service
)
from ..agents import AGENT_REGISTRY, get_agent_info
from ..utils.bigquery_helper import BigQueryHelper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory stores for demo purposes
CHAT_HISTORY = {}
FEEDBACK_STORE = []

def get_bigquery_helper() -> BigQueryHelper:
    """BigQuery 헬퍼 인스턴스 반환"""
    return BigQueryHelper()

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """사용자 질의 처리 엔드포인트"""
    return await process_query_service(request, bq_helper)

@router.post("/query-stream")
async def process_query_stream(
    request: QueryRequest,
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """사용자 질의 실시간 스트리밍 엔드포인트"""
    agent_info = get_agent_info("divorce_case")
    
    return StreamingResponse(
        stream_adk_events_service(
            executor_agent_info=agent_info,
            display_agent_info=agent_info,
            agent_mode="unified",
            user_message=request.message,
            user_id=request.user_id or "anonymous",
            session_id=request.session_id or "default"
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )

@router.get("/agents", response_model=List[AgentSummary])
async def list_agents() -> List[AgentSummary]:
    """사용 가능한 에이전트 목록 조회"""
    summaries = []
    for info in AGENT_REGISTRY.values():
        summaries.append(
            AgentSummary(
                key=info.key,
                display_name=info.display_name,
                description=info.description,
                focus=info.focus,
                strengths=info.strengths,
                keywords=info.keywords,
                active=info.active,
            )
        )
    return summaries

@router.get("/examples", response_model=List[ExampleQuery])
async def get_example_queries() -> List[ExampleQuery]:
    """예시 질의 목록 조회"""
    return [
        ExampleQuery(
            id="divorce_evidence",
            category="증거 분석",
            question="제가 제출한 카톡 대화 내용이 이혼 소송에서 증거로 사용될 수 있을까요?",
            description="제출된 증거의 법적 효력과 의미를 분석합니다"
        ),
        ExampleQuery(
            id="precedent_alimony",
            category="판례 통계",
            question="최근 3년간 서울가정법원의 평균 위자료 액수는 얼마인가요?",
            description="BigQuery 판례 데이터를 기반으로 위자료 통계를 제공합니다"
        ),
        ExampleQuery(
            id="legal_division",
            category="재산 분할",
            question="결혼 전 취득한 특유재산도 재산 분할 대상에 포함되나요?",
            description="재산 분할 원칙과 예외 상황에 대해 상담합니다"
        )
    ]

@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """파일 업로드 처리"""
    import os, uuid, shutil
    try:
        upload_dir = os.path.join(os.getcwd(), "data", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        unique_filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return UploadResponse(
            file_path=file_path,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            size=os.path.getsize(file_path),
            file_url=f"/uploads/{unique_filename}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")

@router.get("/history/{user_id}", response_model=HistoryResponse)
async def get_chat_history(user_id: str, limit: int = 10):
    """채팅 내역 조회"""
    user_msgs = CHAT_HISTORY.get(user_id, [])
    user_msgs.sort(key=lambda x: getattr(x, 'timestamp', 0), reverse=True)
    return HistoryResponse(messages=user_msgs[:limit])

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    """피드백 제출"""
    FEEDBACK_STORE.append(feedback)
    return FeedbackResponse(status="success", message="Feedback received")
