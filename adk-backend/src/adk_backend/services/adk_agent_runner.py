from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


async def run_adk_agent(
    agent: Any,
    user_message: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a Google ADK agent with the provided user message and capture the trace.

    Returns:
        Dict[str, Any]: agent_response, tool_calls, sql_query, query_result, events_count
    """
    logger.info("=" * 100)
    logger.info("🚀 [ADK 실행] Google ADK Agent 실행 시작")
    logger.info("=" * 100)

    runner = InMemoryRunner(app_name="ADK Chat", agent=agent)
    logger.info(f"✅ [ADK] Runner 생성 완료 (agent={agent.name})")

    resolved_user = user_id or "web-user"
    resolved_session = session_id or f"chat-{resolved_user}"

    logger.info(f"🔐 [ADK] 세션 생성 중... (user={resolved_user}, session={resolved_session})")
    session = await runner.session_service.create_session(
        app_name="ADK Chat",
        user_id=resolved_user,
        session_id=resolved_session,
    )
    logger.info(f"✅ [ADK] 세션 생성 완료 (user_id={session.user_id}, session_id={session.id})")

    message = genai_types.Content(role="user", parts=[genai_types.Part(text=user_message)])

    events = []
    tool_calls = []
    agent_response = ""
    sql_query = None
    query_result = None

    logger.info("")
    logger.info("-" * 100)
    logger.info(f"📨 [ADK 메시지] {user_message}")
    logger.info("-" * 100)
    logger.info("🔄 [ADK] Agent 실행 시작... 이벤트 수신 대기 중...")
    logger.info("-" * 100)

    event_count = 0
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=message,
    ):
        event_count += 1
        events.append(event)

        event_type = getattr(event, "__class__", type(event)).__name__
        logger.info("")
        logger.info(f"🎯 [ADK 이벤트 #{event_count}] 타입: {event_type}")

        event_attrs = []
        for attr in [
            "content",
            "parts",
            "text",
            "function_name",
            "function_call",
            "function_response",
            "function_args",
        ]:
            if hasattr(event, attr):
                event_attrs.append(attr)
        if event_attrs:
            logger.info(f"   📋 속성: {', '.join(event_attrs)}")

        if hasattr(event, "content") and event.content:
            content = event.content
            logger.info(f"   📦 Content 상세:")
            logger.info(f"      - Role: {getattr(content, 'role', 'N/A')}")
            if hasattr(content, "parts") and content.parts:
                logger.info(f"      - Parts 개수: {len(content.parts)}")
                for part_idx, part in enumerate(content.parts, 1):
                    part_type = type(part).__name__
                    logger.info(f"      - Part #{part_idx}: {part_type}")

                    if hasattr(part, "text") and part.text:
                        logger.info(f"         * text ({len(part.text)}자): {part.text[:100]}...")

                    if hasattr(part, "function_call"):
                        fc = part.function_call
                        tool_name = getattr(fc, "name", None) or "unknown_tool"
                        tool_args = getattr(fc, "args", {})
                        role = getattr(content, "role", None)

                        logger.info(f"         * function_call: {tool_name}")
                        if tool_args:
                            logger.info(f"         * args: {tool_args}")

                        if role == "model" and tool_name != "unknown_tool":
                            logger.info("")
                            logger.info(f"🛠️  [ADK 도구 호출 #{len(tool_calls) + 1}]")
                            logger.info(f"   📌 도구명: {tool_name}")
                            logger.info(f"   📝 전체 인자:")
                            logger.info(f"   {json.dumps(tool_args, indent=6, ensure_ascii=False)}")

                            tool_calls.append(
                                {
                                    "tool_name": tool_name,
                                    "args": tool_args,
                                }
                            )
                        elif tool_name == "unknown_tool":
                            logger.debug(f"         ⏭️  Internal event (unknown_tool, role={role}) - skipped")

                        if (
                            role == "model"
                            and tool_name in ["bigquery_execute", "bigquery.execute"]
                            and "sql" in tool_args
                        ):
                            if not sql_query:
                                sql_query = tool_args["sql"]
                                logger.info("")
                                logger.info("💾 [SQL 쿼리 추출 - function_call에서]")
                                logger.info("   📜 SQL:")
                                logger.info(sql_query)
                                logger.info("")

                    if hasattr(part, "function_response"):
                        fr = part.function_response
                        logger.info("         * function_response 존재")

                        response_data = None
                        if hasattr(fr, "response"):
                            response_data = fr.response
                        elif isinstance(fr, dict):
                            response_data = fr
                        elif isinstance(fr, str):
                            try:
                                response_data = json.loads(fr)
                            except Exception:
                                response_data = fr

                        if response_data:
                            logger.info("")
                            logger.info("📥 [ADK 도구 응답 수신]")
                            logger.info(f"   📝 응답 타입: {type(response_data).__name__}")

                            response_str = str(response_data)
                            if len(response_str) > 500:
                                logger.info("   📄 응답 내용 (처음 500자):")
                                logger.info(f"   {response_str[:500]}...")
                                logger.info(f"   ... (총 {len(response_str)}자)")
                            else:
                                logger.info("   📄 응답 내용:")
                                logger.info(f"   {response_str}")

                            if isinstance(response_data, str):
                                try:
                                    response_data = json.loads(response_data)
                                    logger.info("   ✅ JSON 파싱 성공")
                                    logger.info(
                                        f"   📊 JSON 키: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}"
                                    )
                                except json.JSONDecodeError as exc:
                                    logger.warning(f"   ⚠️  JSON 파싱 실패: {exc}")

                            if isinstance(response_data, dict):
                                if "rows" in response_data:
                                    query_result = response_data["rows"]
                                    row_count = (
                                        len(query_result)
                                        if isinstance(query_result, list)
                                        else "N/A"
                                    )
                                    logger.info("📊 [쿼리 결과 추출 성공]")
                                    logger.info(f"   📈 행 개수: {row_count}")
                                    if isinstance(query_result, list) and query_result:
                                        logger.info("   📝 첫 번째 행 샘플:")
                                        logger.info(
                                            json.dumps(
                                                query_result[0],
                                                indent=6,
                                                ensure_ascii=False,
                                            )
                                        )
                                if tool_calls:
                                    tool_calls[-1]["response"] = response_data

                    if hasattr(part, "thought_signature"):
                        logger.info("         * thought_signature 존재 (Agent 내부 사고)")

        if hasattr(event, "text") and event.text:
            agent_response += event.text
            logger.info(f"   💬 텍스트 수신 ({len(event.text)}자): {event.text[:200]}...")
        elif hasattr(event, "content") and hasattr(event.content, "parts"):
            for part_idx, part in enumerate(event.content.parts, 1):
                if hasattr(part, "text") and part.text:
                    agent_response += part.text
                    logger.info(
                        f"   💬 파트 #{part_idx} 텍스트 수신 ({len(part.text)}자): {part.text[:200]}..."
                    )

    logger.info("")
    logger.info("=" * 100)
    logger.info("✅ [ADK 실행 완료]")
    logger.info("=" * 100)
    logger.info(f"   📊 총 이벤트: {len(events)}개")
    logger.info(f"   🛠️  도구 호출: {len(tool_calls)}회")
    logger.info(f"   💬 응답 텍스트: {len(agent_response)}자")
    logger.info(f"   💾 SQL 쿼리: {'✅ 생성됨' if sql_query else '❌ 없음'}")
    logger.info(f"   📈 쿼리 결과: {'✅ 있음' if query_result else '❌ 없음'}")

    if tool_calls:
        logger.info("")
        logger.info("🔧 [도구 호출 요약]")
        for idx, tc in enumerate(tool_calls, 1):
            logger.info(f"   {idx}. {tc['tool_name']}")

    if agent_response:
        logger.info("")
        logger.info("💬 [Agent 최종 응답]")
        if len(agent_response) > 300:
            logger.info(f"   (처음 300자): {agent_response[:300]}...")
            logger.info(f"   ... (총 {len(agent_response)}자)")
        else:
            logger.info(f"   {agent_response}")

    if sql_query:
        logger.info("")
        logger.info("💾 [생성된 SQL]")
        logger.info(sql_query)

    if query_result:
        result_count = len(query_result) if isinstance(query_result, list) else "N/A"
        logger.info("")
        logger.info("📊 [쿼리 결과]")
        logger.info(f"   행 개수: {result_count}")
        if isinstance(query_result, list) and query_result:
            logger.info("   첫 번째 행:")
            logger.info(json.dumps(query_result[0], indent=6, ensure_ascii=False))

    logger.info("=" * 100)

    return {
        "agent_response": agent_response.strip(),
        "tool_calls": tool_calls,
        "sql_query": sql_query,
        "query_result": query_result,
        "events_count": len(events),
    }

