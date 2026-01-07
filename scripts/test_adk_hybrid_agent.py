#!/usr/bin/env python3
"""
[ADK 최소 기능 예제] 도구 선택(Tool Selection) 능력을 가진 하이브리드 에이전트
-----------------------------------------------------------------------
이 스크립트는 두 가지 서로 다른 도구를 가진 에이전트가
질문의 의도에 따라 적절한 도구를 스스로 선택(Routing)하는 것을 보여줍니다.

장착된 도구:
1. `bigquery_execute`: 통계, 집계, 숫자 계산 (예: "몇 건이야?", "비율은?")
2. `search_precedents`: 판례 상세 검색, 법리 해석 (예: "~한 경우 이혼 되나요?", "판례 찾아줘")

검증 시나리오:
- 시나리오 A: 통계 질문 -> BigQuery 도구 호출 확인
- 시나리오 B: 법리 질문 -> File Search 도구 호출 확인
"""

import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 1. 경로 설정
project_root = Path(__file__).resolve().parent.parent
backend_src = project_root / "adk-backend" / "src"
sys.path.append(str(backend_src))

# 환경 변수 로드
load_dotenv(project_root / ".env")

try:
    from google.adk.agents import Agent
    from google.adk.tools import FunctionTool
    from google.adk.runners import InMemoryRunner
    from google.genai import types as genai_types
    
    # 두 가지 도구 모두 임포트
    from adk_backend.tools.bigquery import bigquery_execute
    from adk_backend.tools.file_search import search_precedents
    from adk_backend.config import get_settings
except ImportError as e:
    print("❌ ADK 또는 백엔드 모듈 임포트 실패.")
    sys.exit(1)

async def run_scenario(runner, user_id, session_id, query_text):
    """단일 시나리오 실행 함수"""
    print(f"\n📝 질문: {query_text}")
    print("⏳ 에이전트가 도구를 고민 중입니다...\n")

    message = genai_types.Content(
        role="user", 
        parts=[genai_types.Part(text=query_text)]
    )

    tool_used = []

    async for event in runner.run_async(
        user_id=user_id, 
        session_id=session_id, 
        new_message=message
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    tool_name = fc.name
                    tool_used.append(tool_name)
                    print(f"   🛠️  [도구 선택됨] {tool_name}")
                    
                    if tool_name == "bigquery_execute" and "sql" in fc.args:
                        print(f"       (SQL 생성): {fc.args['sql']}")
                    elif tool_name == "precedent_search" and "query" in fc.args:
                         print(f"       (검색어): {fc.args['query']}")

                if hasattr(part, "function_response") and part.function_response:
                    print(f"   📥 [결과 수신] {part.function_response.name}")

    return tool_used

async def main():
    print("=" * 70)
    print("🤖 ADK 하이브리드 에이전트 테스트 (BigQuery + RAG)")
    print("=" * 70)

    settings = get_settings()
    
    # 두 가지 능력을 모두 가진 에이전트 정의
    hybrid_agent = Agent(
        name="hybrid_divorce_agent",
        description="통계 분석과 판례 검색이 모두 가능한 이혼 전문가",
        model=settings.adk_model_name,
        instruction=(
            "너는 유능한 이혼 법률/데이터 전문가야.\n"
            "사용자의 질문에 따라 다음 두 도구 중 하나를 선택해서 사용해:\n\n"
            "1. `bigquery_execute`: '몇 건이야?', '비율은?', '통계' 같은 질문에 사용해.\n"
            "   (테이블: `divorce_analytics.precedent_cases`, 컬럼: fault_type, alimony_amount 등)\n\n"
            "2. `search_precedents`: 구체적인 판례 내용, 법적 쟁점, '이런 경우 이혼 되나요?' 같은 질문에 사용해.\n"
            "   (RAG 기반 원문 검색)\n\n"
            "반드시 질문의 의도를 파악하고 적절한 도구를 골라서 실행해줘."
        ),
        tools=[
            FunctionTool(bigquery_execute),     # Tool A
            FunctionTool(search_precedents)     # Tool B
        ]
    )

    print("🔹 실행기(InMemoryRunner) 준비 완료")
    runner = InMemoryRunner(app_name="adk_hybrid_test", agent=hybrid_agent)
    
    # 세션 준비
    user_id = "hybrid-user"
    session_id = "hybrid-session-001"
    try:
        await runner.session_service.create_session(
            app_name="adk_hybrid_test", user_id=user_id, session_id=session_id
        )
    except: pass

    # --- 시나리오 1: 통계 질문 ---
    print("\n🔽 [시나리오 1] 통계형 질문 (BigQuery 예상)")
    print("-" * 40)
    tools_1 = await run_scenario(
        runner, user_id, session_id, 
        "전체 판례 중에 위자료가 가장 높았던 건 얼마야?"
    )
    
    # --- 시나리오 2: 검색 질문 ---
    print("\n🔽 [시나리오 2] 탐색형 질문 (File Search 예상)")
    print("-" * 40)
    tools_2 = await run_scenario(
        runner, user_id, session_id,
        "배우자가 도박에 빠졌는데 이걸로 이혼 소송 걸 수 있어? 관련 판례 찾아줘."
    )

    # 결과 검증
    print("\n" + "=" * 70)
    print("✅ 테스트 결과 요약")
    print("=" * 70)
    print(f"1. 통계 질문 도구: {tools_1} -> {'성공 (BigQuery)' if 'bigquery_execute' in tools_1 else '실패'}")
    print(f"2. 검색 질문 도구: {tools_2} -> {'성공 (RAG)' if 'precedent_search' in tools_2 or 'search_precedents' in tools_2 else '실패'}")

if __name__ == "__main__":
    asyncio.run(main())
