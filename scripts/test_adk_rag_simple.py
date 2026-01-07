#!/usr/bin/env python3
"""
[ADK 최소 기능 예제] 단일 RAG 도구를 사용한 ADK 코어 테스트
-----------------------------------------------------------
이 스크립트는 가장 최소한의 설정으로 ADK의 핵심 작동 루프를 보여줍니다.
다음 요소들의 상호작용을 검증합니다:
1. 에이전트 생성 (google.adk.agents.Agent)
2. 도구 바인딩 (google.adk.tools.function_tool.FunctionTool)
3. InMemoryRunner를 통한 실행
4. 세션 관리 및 메시지 객체 생성

사전 조건:
- `adk-backend` 의존성이 설치되어 있어야 합니다.
- 필요시 `pip install -e adk-backend`를 실행하거나 백엔드 venv를 사용하세요.
"""

import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 1. 경로 설정: adk_backend를 임포트할 수 있도록 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
backend_src = project_root / "adk-backend" / "src"
sys.path.append(str(backend_src))

# 환경 변수 로드 (.env)
load_dotenv(project_root / ".env")

# 2. ADK 및 백엔드 모듈 임포트
try:
    from google.adk.agents import Agent
    from google.adk.tools import FunctionTool
    from google.adk.runners import InMemoryRunner
    from google.genai import types as genai_types # 메시지 객체 생성을 위해 필요
    
    # 테스트할 특정 RAG 도구 임포트 (판례 검색)
    from adk_backend.tools.file_search import search_precedents
    from adk_backend.config import get_settings
except ImportError as e:
    print("❌ ADK 또는 백엔드 모듈 임포트 실패.")
    print(f"오류: {e}")
    print("💡 힌트: 백엔드 환경(venv)에서 실행 중인지 확인하세요.")
    print("   시도: source adk-backend/venv/bin/activate && python scripts/test_adk_rag_simple.py")
    sys.exit(1)

async def main():
    print("=" * 60)
    print("🤖 ADK 최소 에이전트 테스트: RAG 전용 모드")
    print("=" * 60)

    # 3. 최소 기능 에이전트 생성
    print("🔹 에이전트(Agent) 생성 중...")
    settings = get_settings()
    
    minimal_agent = Agent(
        name="minimal_rag_agent",
        description="RAG 기능 테스트를 위한 최소 에이전트",
        model=settings.adk_model_name,
        instruction=(
            "너는 판례 검색을 위한 최소 기능 에이전트야.\n"
            "사용자의 질문에 대해 반드시 `search_precedents` 도구를 사용해서 판례를 검색하고,\n"
            "그 결과를 요약해서 답변해줘."
        ),
        tools=[
            FunctionTool(search_precedents)
        ]
    )

    # 4. 실행기(Runner) 및 세션 생성
    print("🔹 메모리 내 실행기(InMemoryRunner) 초기화...")
    runner = InMemoryRunner(app_name="adk_minimal_test", agent=minimal_agent)
    
    # 세션 생성 (ADK는 세션 기반으로 상태를 관리합니다)
    user_id = "test-user"
    session_id = "test-session-001"
    
    print(f"🔹 세션 생성 중... (User: {user_id}, Session: {session_id})")
    try:
        session = await runner.session_service.create_session(
            app_name="adk_minimal_test",
            user_id=user_id,
            session_id=session_id,
        )
    except Exception as e:
        # 이미 세션이 있을 수 있음
        print(f"   (세션 생성 참고: {e})")

    # 5. 질문 실행
    query_text = "최근 혼인 무효와 관련된 대법원 판례가 변경된게 있어? 상세히 찾아줘."
    print(f"\n📝 질문: {query_text}")
    print("⏳ 에이전트 생각 중... (도구 호출 대기)\n")

    # [중요] Runner에 전달할 메시지 객체 생성 (String이 아닌 Content 객체여야 함)
    message = genai_types.Content(
        role="user", 
        parts=[genai_types.Part(text=query_text)]
    )

    # 6. 실행 루프
    # run_async는 이벤트를 스트리밍합니다.
    async for event in runner.run_async(
        user_id=user_id, 
        session_id=session_id, 
        new_message=message
    ):
        # 이벤트 타입 확인
        event_type = type(event).__name__
        
        # 1) 텍스트 응답 (Thought 또는 답변)
        if hasattr(event, "text") and event.text:
            # 너무 긴 텍스트는 잘라서 보여줌
            # print(f"   💬 [Text] {event.text[:50]}...")
            pass

        # 2) 콘텐츠 객체 (Function Call 포함)
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                # 도구 호출(Function Call) 감지
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    print(f"   🛠️  [도구 호출 감지] {fc.name}")
                    if hasattr(fc, "args"):
                         print(f"       인자: {fc.args}")
                
                # 도구 응답(Function Response) 감지
                if hasattr(part, "function_response") and part.function_response:
                    print(f"   📥 [도구 응답 수신] {part.function_response.name}")

    print("\n✅ 실행 완료.")
    print("-" * 60)
    print("위 로그에 '[도구 호출 감지] precedent_search'가 보이면 성공입니다.")

if __name__ == "__main__":
    asyncio.run(main())
