#!/usr/bin/env python3
"""
[ADK 심화 예제] Implicit CAG(Context Caching) vs Explicit CAG(Tool Use) 실험
----------------------------------------------------------------------------
이 스크립트는 지식을 제공하는 두 가지 방식이 에이전트 행동에 미치는 차이를 증명합니다.
이 실험을 통해 "비용 절감"과 "응답 속도" 사이의 트레이드오프를 이해할 수 있습니다.

실험 구성:
1. Explicit Agent (명시적): 지식이 없음. 도구(`search_secret_info`)를 호출해야만 답을 알 수 있음.
   -> RAG 방식 (검색 비용 발생, 라운드트립 발생)
2. Implicit Agent (암시적): 지문(시스템 프롬프트)에 지식이 이미 포함되어 있음.
   -> Context Caching 방식 (토큰 비용 발생, 즉각 응답)

테스트 질문: "코드명 '프로젝트 델타'의 비밀번호는 뭐야?"
"""

import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
backend_src = project_root / "adk-backend" / "src"
sys.path.append(str(backend_src))
load_dotenv(project_root / ".env")

try:
    from google.adk.agents import Agent
    from google.adk.tools import FunctionTool
    from google.adk.runners import InMemoryRunner
    from google.genai import types as genai_types
    from adk_backend.config import get_settings
except ImportError:
    sys.exit(1)

# --- 1. 더미 도구 정의 (Explicit Agent용) ---
def lookup_secret_db(project_name: str):
    """
    [도구] 프로젝트 이름을 입력하면 비밀번호를 찾아줍니다.
    """
    if "델타" in project_name or "Delta" in project_name:
        return "비밀번호는 'BlueSky_2024' 입니다."
    return "정보가 없습니다."

# ---------------------------------------------

async def run_agent_test(agent_name, agent, question):
    print(f"\n🏃‍♂️ [{agent_name}] 에이전트 실행 중...")
    
    runner = InMemoryRunner(app_name=f"test_{agent_name}", agent=agent)
    session_id = f"session_{agent_name}"
    user_id = "tester"
    
    try:
        await runner.session_service.create_session(
            app_name=f"test_{agent_name}", 
            user_id=user_id, 
            session_id=session_id
        )
    except: pass

    message = genai_types.Content(
        role="user", 
        parts=[genai_types.Part(text=question)]
    )

    events = []
    async for event in runner.run_async(
        user_id=user_id, 
        session_id=session_id, 
        new_message=message
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    print(f"   🛠️  도구 호출 감지: {part.function_call.name}")
                    events.append("Tool Call")
                if hasattr(part, "function_response") and part.function_response:
                    print(f"   📥 도구 결과 수신: {part.function_response.name}")

        if hasattr(event, "text") and event.text:
            # 텍스트 응답의 일부만 출력
            preview = event.text.strip().replace("\n", " ")
            if preview:
                print(f"   💬 텍스트 응답: {preview[:50]}...")
                events.append("Text Response")

    return events

async def main():
    print("=" * 70)
    print("⚖️  CAG 실험: Implicit(캐싱/프롬프트) vs Explicit(도구사용)")
    print("=" * 70)

    settings = get_settings()
    question = "코드명 '프로젝트 델타'의 비밀번호는 뭐야?"
    print(f"❓ 질문: {question}\n")

    # --- Case 1: Explicit Agent (Tools) ---
    explicit_agent = Agent(
        name="explicit_agent",
        description="지식이 없어 도구를 써야 하는 에이전트",
        model=settings.adk_model_name,
        instruction=(
            "너는 보안 요원이야. 아는 것이 없으므로 정보가 필요하면 반드시 도구를 조회해."
        ),
        tools=[FunctionTool(lookup_secret_db)]
    )

    events_1 = await run_agent_test("Explicit_CAG", explicit_agent, question)

    # --- Case 2: Implicit Agent (Context/Prompt) ---
    # 지식을 프롬프트에 직접 주입 (Context Caching 상황 시뮬레이션)
    secret_context = """
    [비밀 정보]
    - 프로젝트 알파: 1234
    - 프로젝트 델타: BlueSky_2024
    - 프로젝트 오메가: 0000
    """
    
    implicit_agent = Agent(
        name="implicit_agent",
        description="지식을 이미 머릿속에 담고 있는 에이전트 (Context Cached)",
        model=settings.adk_model_name,
        instruction=(
            f"너는 보안 요원이야. 다음 정보를 이미 외우고 있어.\n{secret_context}\n"
            "사용자가 물어보면 도구 없이 즉시 대답해."
        ),
        tools=[] # 도구 없음
    )

    events_2 = await run_agent_test("Implicit_CAG", implicit_agent, question)

    # --- 결과 비교 ---
    print("\n" + "=" * 70)
    print("📊 실험 결과 분석")
    print("=" * 70)
    
    has_tool_call_1 = "Tool Call" in events_1
    has_tool_call_2 = "Tool Call" in events_2

    print(f"1. Explicit Agent (RAG 방식): 도구 호출 {'⭕ 있음' if has_tool_call_1 else '❌ 없음'}")
    print(f"   -> 외부 지식을 가져오기 위해 '검색 비용'과 '지연 시간'이 발생함.")
    
    print(f"\n2. Implicit Agent (Caching 방식): 도구 호출 {'⭕ 있음' if has_tool_call_2 else '❌ 없음'}")
    print(f"   -> 지식이 모델 내부에 있어 '즉각 응답'함. (대신 토큰 저장 비용 발생)")
    print("-" * 70)

if __name__ == "__main__":
    asyncio.run(main())
