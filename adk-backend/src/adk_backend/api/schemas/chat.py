#!/usr/bin/env python3
"""
채팅 관련 API 스키마
"""

from pydantic import BaseModel, Field, AliasChoices, ConfigDict
from typing import List, Optional, Dict, Any, Annotated, Literal
from datetime import datetime

class ChatMessage(BaseModel):
    role: str  # 'user' 또는 'assistant'
    content: str
    timestamp: Optional[datetime] = None

MessageField = Annotated[
    str,
    Field(validation_alias=AliasChoices("message", "query"), min_length=1),
]

class QueryRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: MessageField
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    sql_mode: Optional[str] = Field(
        default="template",
        description="SQL 생성 방식: 'template' (하드코드 힌트 + SQL 조립)"
    )
    agent_type: Optional[Literal["sql", "conversational"]] = Field(
        default="sql",
        description="에이전트 종류 선택: SQL (도구 기반) 또는 Conversational (자연어 분석)"
    )
    files: Optional[List[str]] = Field(default=None, description="첨부 파일 경로 목록")

class QueryResponse(BaseModel):
    response: str
    sql_query: Optional[str] = None
    query_result: Optional[List[Dict[str, Any]]] = None
    chart_suggestion: Optional[str] = None
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None
    analysis_steps: List[str] = Field(default_factory=list)
    sql_mode: Optional[str] = None
    adk_agent: Optional[str] = None
    adk_model: Optional[str] = None
    agent_metadata: Optional[Dict[str, Any]] = None
    execution_trace: List[Dict[str, Any]] = Field(default_factory=list)
    sql_generation_details: Optional[Dict[str, Any]] = None

class ExampleQuery(BaseModel):
    id: str
    category: str
    question: str
    description: str

class AgentSummary(BaseModel):
    key: str
    display_name: str
    description: str
    focus: str
    strengths: List[str]
    keywords: List[str]
    active: bool

class FeedbackRequest(BaseModel):
    user_id: str
    message_id: str
    feedback_type: Literal["like", "dislike"]
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    status: str
    message: str

class SavedMessage(BaseModel):
    id: str
    sender: str
    content: str
    timestamp: datetime
    queryResult: Optional[Dict[str, Any]] = None

class HistoryResponse(BaseModel):
    messages: List[SavedMessage]

class UploadResponse(BaseModel):
    file_path: str
    filename: str
    content_type: str
    size: int
    file_url: Optional[str] = None
