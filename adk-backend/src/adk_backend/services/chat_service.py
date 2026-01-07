#!/usr/bin/env python3
"""
채팅 비즈니스 로직 서비스
"""

import json
import logging
import asyncio
import os
import uuid
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any, AsyncGenerator

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from google.genai import types as genai_types
from google.adk.runners import InMemoryRunner

from ..agents import (
    divorce_case_agent,
    AgentInfo,
    get_agent_info,
)
from ..utils.bigquery_helper import BigQueryHelper
from ..services.adk_agent_runner import run_adk_agent
from ..api.schemas.chat import (
    QueryRequest, QueryResponse, ChatMessage, AgentSummary, 
    ExampleQuery, UploadResponse, FeedbackRequest, FeedbackResponse, 
    HistoryResponse, SavedMessage
)

# ADK 플러그인 (필요한 경우 직접 정의하거나 임포트)
# ReflectAndRetryToolPlugin은 google.adk.plugins.retry에서 가져오거나 
# chat.py에 정의되어 있다면 여기로 가져와야 함.
# chat.py를 다시 확인해보니 ReflectAndRetryToolPlugin이 임포트된 것 같지는 않고 
# chat.py 내부에 정의되어 있지도 않음. 
# 하지만 InMemoryRunner 세션 생성 전 호출됨.
# 일단 chat_service.py에 필요한 유틸리티 함수들을 먼저 정의함.

logger = logging.getLogger(__name__)

def _preview_data(data: Any, limit: int = 200) -> Optional[str]:
    """UI에 표시하기 쉬운 응답 요약 텍스트."""
    if data is None:
        return None

    if isinstance(data, (int, float, bool)):
        return str(data)

    if isinstance(data, str):
        return data if len(data) <= limit else f"{data[:limit]}..."

    try:
        serialized = json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        serialized = str(data)

    return serialized if len(serialized) <= limit else f"{serialized[:limit]}..."

async def process_query_service(
    request: QueryRequest,
    bq_helper: BigQueryHelper
) -> QueryResponse:
    """사용자 질의 처리 핵심 로직"""
    try:
        start_time = datetime.now()
        analysis_steps: List[str] = []
        analysis_steps.append(f"질문 수신: {request.message}")
        execution_trace: List[Dict[str, Any]] = []
        sql_generation_details: Dict[str, Any] = {"mode": None, "attempts": []}
        agent_metadata: Optional[Dict[str, Any]] = None

        logger.info("="*80)
        logger.info(f"📨 [서비스] 사용자 질문: {request.message}")
        
        # 파일 컨텍스트 추가
        effective_message = request.message
        if request.files:
            file_context = "\n\n[System: The user has attached the following files for analysis:]\n"
            for file_path in request.files:
                file_context += f"- {file_path}\n"
            effective_message += file_context

        # 에이전트 정보 설정
        agent_info = get_agent_info("divorce_case")
        selected_agent = divorce_case_agent
        agent_name = getattr(selected_agent, "name", "divorce_total_expert")
        agent_reason = "통합 이혼 솔루션 에이전트 자동 할당"
        agent_mode = "unified"
        
        use_adk_agent = True
        effective_sql_mode = "unified"

        agent_metadata = {
            "key": agent_info.key,
            "display_name": agent_info.display_name,
            "description": agent_info.description,
            "focus": agent_info.focus,
            "strengths": agent_info.strengths,
            "keywords": agent_info.keywords,
        }

        execution_trace.append({
            "phase": "agent_selection",
            "agent": agent_metadata,
            "reason": agent_reason,
            "mode": agent_mode,
            "tools": [
                getattr(tool.func, "__name__", "unknown")
                if hasattr(tool, "func") else str(tool)
                for tool in selected_agent.tools
            ],
        })

        sql_query = None
        response_text = ""
        adk_result = None
        query_result = None

        # ===== ADK Agent 실행 =====
        try:
            adk_result = await run_adk_agent(
                agent=selected_agent,
                user_message=effective_message,
                user_id=request.user_id or "anonymous",
                session_id=request.session_id or "default"
            )

            # 도구 호출 정보 처리
            if adk_result["tool_calls"]:
                for i, tool_call in enumerate(adk_result["tool_calls"], 1):
                    tool_name = tool_call["tool_name"]
                    analysis_steps.append(f"🛠️  ADK 도구 #{i}: {tool_name}")
                    response_data = tool_call.get("response")
                    response_summary: Dict[str, Any] = {}
                    if isinstance(response_data, dict):
                        if "rows" in response_data:
                            rows = response_data.get("rows", [])
                            response_summary["row_count"] = len(rows) if isinstance(rows, list) else rows
                        if "schema" in response_data:
                            schema = response_data.get("schema", [])
                            response_summary["schema_fields"] = len(schema) if isinstance(schema, list) else schema
                    
                    execution_trace.append({
                        "phase": "adk_tool_call",
                        "order": i,
                        "tool_name": tool_name,
                        "args": tool_call.get("args"),
                        "response_preview": _preview_data(response_data),
                        "response_summary": response_summary or None,
                    })

            # SQL 및 결과 추출
            if adk_result["sql_query"]:
                sql_query = adk_result["sql_query"]
                analysis_steps.append("SQL 생성: ADK Agent가 생성함")
                sql_generation_details.update({
                    "mode": "adk",
                    "source": "google_adk_agent",
                    "sql_preview": _preview_data(sql_query, limit=500),
                })
                execution_trace.append({
                    "phase": "sql_generated",
                    "mode": "adk",
                    "sql_preview": _preview_data(sql_query, limit=500),
                })

            if adk_result["query_result"]:
                query_result = adk_result["query_result"]
                analysis_steps.append(f"BigQuery 실행: ADK Agent가 실행함 ({len(query_result)}행)")
                execution_trace.append({
                    "phase": "query_execution",
                    "executor": "adk_agent",
                    "row_count": len(query_result),
                })

            if adk_result["agent_response"]:
                response_text = adk_result["agent_response"]
                execution_trace.append({
                    "phase": "agent_response",
                    "source": "adk_agent",
                    "character_count": len(response_text),
                })

        except Exception as e:
            logger.error(f"❌ [서비스] ADK 실행 오류: {e}")
            analysis_steps.append(f"❌ ADK Agent 실행 실패: {str(e)}")
            use_adk_agent = False

        # Fallback 및 기타 로직 (SELECT 쿼리 실행 등)
        if not use_adk_agent or (use_adk_agent and adk_result and not adk_result.get("query_result")):
            if sql_query and sql_query.strip().upper().startswith('SELECT'):
                try:
                    query_result = bq_helper.execute_query(sql_query)
                    analysis_steps.append(f"BigQuery 실행 성공: {len(query_result)}행 반환")
                except Exception as e:
                    logger.error(f"❌ [서비스] 쿼리 실행 오류: {e}")
                    analysis_steps.append(f"BigQuery 실행 실패: {str(e)}")

        # 차트 제안
        chart_suggestion = "table" if query_result else None

        execution_time = (datetime.now() - start_time).total_seconds()
        
        return QueryResponse(
            response=response_text or "응답을 생성할 수 없습니다.",
            sql_query=sql_query,
            query_result=query_result,
            chart_suggestion=chart_suggestion,
            execution_time=execution_time,
            analysis_steps=analysis_steps,
            sql_mode=effective_sql_mode,
            adk_agent=agent_name if use_adk_agent else None,
            adk_model=selected_agent.model if use_adk_agent else None,
            agent_metadata=agent_metadata,
            execution_trace=execution_trace,
            sql_generation_details=sql_generation_details if sql_generation_details.get("mode") else None,
        )

    except Exception as e:
        logger.error(f"❌ [서비스] 예상치 못한 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def stream_adk_events_service(
    executor_agent_info: AgentInfo,
    display_agent_info: AgentInfo,
    agent_mode: str,
    user_message: str,
    user_id: str,
    session_id: str
) -> AsyncGenerator[str, None]:
    """SSE 스트리밍 서비스 핵심 로직"""
    try:
        agent = executor_agent_info.agent
        logger.info(f"🚀 [SSE 서비스] 스트리밍 시작: {executor_agent_info.key}")

        # 시작 알림
        start_payload = {
            "message": "ADK 스트리밍 시작",
            "agent": agent.name if hasattr(agent, "name") else executor_agent_info.key,
            "agent_key": display_agent_info.key,
            "agent_display_name": display_agent_info.display_name,
            "mode": agent_mode,
        }
        yield f"event: start\ndata: {json.dumps(start_payload, ensure_ascii=False)}\n\n"

        # Runner 및 세션 설정
        runner = InMemoryRunner(app_name="ADK Chat Stream", agent=agent)
        resolved_user = user_id or "web-user"
        resolved_session = session_id or f"chat-stream-{resolved_user}"
        
        session = await runner.session_service.create_session(
            app_name="ADK Chat Stream",
            user_id=resolved_user,
            session_id=resolved_session,
        )

        # 에이전트 정보
        agent_info_payload = {
            "agent_name": agent.name if hasattr(agent, "name") else executor_agent_info.key,
            "agent_key": display_agent_info.key,
            "agent_display_name": display_agent_info.display_name,
            "model": agent.model,
            "description": display_agent_info.description,
            "mode": agent_mode
        }
        yield f"event: agent_info\ndata: {json.dumps(agent_info_payload, ensure_ascii=False)}\n\n"

        message = genai_types.Content(role="user", parts=[genai_types.Part(text=user_message)])
        
        agent_response = ""
        sql_query = None
        query_result = None
        tool_call_count = 0

        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=message,
        ):
            event_type = getattr(event, '__class__', type(event)).__name__

            if hasattr(event, 'content') and event.content:
                content = event.content
                role = getattr(content, 'role', None)

                if hasattr(content, 'parts') and content.parts:
                    for part_idx, part in enumerate(content.parts):
                        # 사고 과정
                        if hasattr(part, 'thought'):
                            yield f"event: thought\ndata: {json.dumps({'thought': str(part.thought)}, ensure_ascii=False)}\n\n"

                        # 텍스트 응답
                        if hasattr(part, 'text') and part.text:
                            agent_response += part.text
                            yield f"event: thinking\ndata: {json.dumps({'text': part.text, 'cumulative_length': len(agent_response)}, ensure_ascii=False)}\n\n"

                        # 도구 호출
                        if hasattr(part, 'function_call') and role == 'model':
                            fc = part.function_call
                            tool_name = getattr(fc, 'name', 'unknown')
                            tool_args = getattr(fc, 'args', {})
                            
                            if tool_name != 'unknown':
                                tool_call_count += 1
                                if 'bigquery' in tool_name and 'sql' in tool_args:
                                    sql_query = tool_args['sql']
                                    yield f"event: sql\ndata: {json.dumps({'sql': sql_query, 'tool': tool_name}, ensure_ascii=False)}\n\n"
                                
                                yield f"event: tool_call\ndata: {json.dumps({'tool_name': tool_name, 'args': tool_args, 'order': tool_call_count}, ensure_ascii=False)}\n\n"

                        # 도구 응답 감지
                        if hasattr(part, 'function_response'):
                            fr = part.function_response
                            response_data = None

                            if hasattr(fr, 'response'):
                                response_data = fr.response
                                if isinstance(response_data, str):
                                    try:
                                        response_data = json.loads(response_data)
                                    except json.JSONDecodeError:
                                        pass
                            elif isinstance(fr, dict):
                                response_data = fr
                            elif isinstance(fr, str):
                                try:
                                    response_data = json.loads(fr)
                                except Exception:
                                    response_data = fr

                            if response_data:
                                if isinstance(response_data, dict):
                                    if 'result' in response_data and isinstance(response_data['result'], str):
                                        try:
                                            response_data = json.loads(response_data['result'])
                                        except json.JSONDecodeError:
                                            pass

                                if isinstance(response_data, dict) and 'rows' in response_data:
                                    query_result = response_data['rows']
                                    row_count = len(query_result) if isinstance(query_result, list) else 0
                                    preview = query_result[:3] if isinstance(query_result, list) else None

                                    yield f"event: result\ndata: {json.dumps({'row_count': row_count, 'preview': preview}, ensure_ascii=False)}\n\n"

            await asyncio.sleep(0.01)

        # 응답 완료 및 종료
        yield f"event: response\ndata: {json.dumps({'response': agent_response.strip(), 'length': len(agent_response)}, ensure_ascii=False)}\n\n"
        
        done_payload = {
            "tool_calls": tool_call_count,
            "sql_generated": sql_query is not None,
            "result_rows": len(query_result) if query_result else 0,
            "mode": agent_mode,
        }
        yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(f"❌ [SSE 서비스] 에러: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
