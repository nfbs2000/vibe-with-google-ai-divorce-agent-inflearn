#!/usr/bin/env python3
"""
[ADK 최소 기능 예제] BigQuery 도구를 사용한 ADK 코어 테스트
-----------------------------------------------------------
이 스크립트는 SQL을 생성하고 실행할 수 있는 에이전트를 시연합니다.
다음 기능들을 검증합니다:
1. BigQuery 도구가 장착된 에이전트 생성
2. Text-to-SQL 능력 (모델 지침 기반)
3. InMemoryRunner를 통한 실행

사전 조건:
- `adk-backend` 설치 필요
- Google Cloud 인증 완료 (GOOGLE_APPLICATION_CREDENTIALS)
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
    
    # BigQuery 도구 임포트
    from adk_backend.tools.bigquery import (
        bigquery_execute,
        bigquery_list_templates
    )
    from adk_backend.config import get_settings
except ImportError as e:
    print("❌ ADK 또는 백엔드 모듈 임포트 실패.")
    sys.exit(1)

async def main():
    print("=" * 60)
    print("🤖 ADK BigQuery 에이전트 테스트 (Text-to-SQL)")
    print("=" * 60)

    settings = get_settings()
    
    # BigQuery를 조회할 수 있는 에이전트 정의
    bq_agent = Agent(
        name="bigquery_agent",
        description="BigQuery에서 이혼 판례 데이터를 조회하는 에이전트",
        model=settings.adk_model_name,
        instruction=(
            "너는 이혼 판례 데이터베이스를 다루는 BigQuery SQL 전문가야.\n"
            "테이블 정보: `divorce_analytics.precedent_cases`\n"
            "주요 컬럼: case_id, fault_type, alimony_amount (int), judgment_date, court_name.\n"
            "요청이 오면 Standard SQL 쿼리를 작성해서 `bigquery_execute` 도구로 실행해.\n"
            "별도 요청이 없으면 결과는 최대 5개로 제한해 (LIMIT 5).\n"
            "데이터 조회 결과를 바탕으로 요약 답변을 해줘."
        ),
        tools=[
            FunctionTool(bigquery_execute),
            FunctionTool(bigquery_list_templates)
        ]
    )

    print("🔹 메모리 내 실행기(InMemoryRunner) 초기화...")
    runner = InMemoryRunner(app_name="adk_bq_test", agent=bq_agent)
    
    # 세션 생성
    user_id = "bq-user"
    session_id = "bq-session-001"
    
    try:
        await runner.session_service.create_session(
            app_name="adk_bq_test",
            user_id=user_id,
            session_id=session_id,
        )
    except Exception:
        pass

    # 질문: 집계(Aggregation) 요청
    query_text = "유책 사유(fault_type)별로 판례가 몇 건씩 있는지 세어줘."
    print(f"\n📝 질문: {query_text}")
    print("⏳ 에이전트가 SQL을 생성하고 실행 중입니다...\n")

    message = genai_types.Content(
        role="user", 
        parts=[genai_types.Part(text=query_text)]
    )

    async for event in runner.run_async(
        user_id=user_id, 
        session_id=session_id, 
        new_message=message
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                # 도구 호출(Function Call) - SQL 생성 확인
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    print(f"   🛠️  [도구 호출] {fc.name}")
                    if "sql" in fc.args:
                        print(f"       💻 생성된 SQL: {fc.args['sql']}")
                
                # 도구 응답(Function Response) - 쿼리 결과 수신
                if hasattr(part, "function_response") and part.function_response:
                    print(f"   📥 [도구 응답] {part.function_response.name}")

    print("\n✅ 실행 완료.")
    print("-" * 60)

if __name__ == "__main__":
    asyncio.run(main())
