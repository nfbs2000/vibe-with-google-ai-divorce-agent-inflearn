#!/usr/bin/env python3
"""
[ADK 심화 예제] Docstring이 에이전트의 도구 선택에 미치는 영향 테스트
------------------------------------------------------------------
이 스크립트는 "코드는 똑같지만 독스트링(설명)만 다른" 두 개의 도구를 정의합니다.
에이전트가 오직 독스트링만을 보고 도구를 선택하는지 실험합니다.

실험 구성:
1. `tool_for_red_fruit`: 실제 기능은 없으나 설명에 "빨간 과일 처리용"이라고 적음.
2. `tool_for_yellow_fruit`: 실제 기능은 없으나 설명에 "노란 과일 처리용"이라고 적음.

우리의 질문:
- "사과에 대해 알려줘" -> 에이전트는 무엇을 선택할까? (예상: Red Tool)
- "바나나에 대해 알려줘" -> 에이전트는 무엇을 선택할까? (예상: Yellow Tool)
"""

import sys
import os
import asyncio
from typing import Any
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
except ImportError as e:
    print(f"❌ ADK 또는 백엔드 모듈 임포트 실패: {e}")
    sys.exit(1)

# --- 실험용 더미 도구 정의 ---

def tool_red(query: str):
    """
    [주의: 이 설명을 AI가 읽습니다]
    이 도구는 사과, 딸기, 체리 등 '빨간색 과일'과 관련된 질문일 때만 사용해야 합니다.
    노란색 과일에는 절대 사용하지 마세요.
    """
    return "🍎 빨간 과일 처리 도구가 실행되었습니다."

def tool_yellow(query: str):
    """
    [주의: 이 설명을 AI가 읽습니다]
    이 도구는 바나나, 레몬, 망고 등 '노란색 과일'과 관련된 질문일 때만 사용해야 합니다.
    빨간색 과일에는 절대 사용하지 마세요.
    """
    return "🍌 노란 과일 처리 도구가 실행되었습니다."

# ---------------------------

async def run_experiment(runner, user_id, session_id, query_text):
    print(f"\n🧪 실험 질문: '{query_text}'")
    
    message = genai_types.Content(
        role="user", 
        parts=[genai_types.Part(text=query_text)]
    )

    tool_called = None

    async for event in runner.run_async(
        user_id=user_id, 
        session_id=session_id, 
        new_message=message
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    tool_called = fc.name
                    print(f"   👉 에이전트의 선택: [{tool_called}]")
                    # 실험 목적 달성했으므로 더 이상 진행 안 보여줘도 됨

    return tool_called

async def main():
    print("=" * 70)
    print("🔬 ADK Docstring 영향력 실험")
    print("   : 코드는 같고 설명(Docstring)만 다를 때 에이전트의 반응")
    print("=" * 70)

    settings = get_settings()
    
    # 실험용 에이전트 생성
    experiment_agent = Agent(
        name="fruit_sorter_agent",
        description="과일 색깔에 따라 도구를 분류하는 실험체",
        model=settings.adk_model_name,
        instruction="사용자의 질문에 맞는 색깔의 도구를 선택하세요.",
        tools=[
            FunctionTool(tool_red),
            FunctionTool(tool_yellow)
        ]
    )

    runner = InMemoryRunner(app_name="adk_docstring_test", agent=experiment_agent)
    user_id = "tester"
    session_id = "exp-session-01"
    
    try:
        await runner.session_service.create_session(
            app_name="adk_docstring_test", 
            user_id=user_id, 
            session_id=session_id
        )
    except Exception as e:
        print(f"세션 생성 오류 (무시됨): {e}")

    # 실험 1: 빨간 과일
    choice1 = await run_experiment(runner, user_id, session_id, "요즘 사과 값이 너무 비싼 것 같아.")
    
    # 실험 2: 노란 과일
    choice2 = await run_experiment(runner, user_id, session_id, "바나나 쉐이크 만드는 법 알려줘.")

    print("\n" + "=" * 70)
    print("📝 실험 결과 보고서")
    print("=" * 70)
    print(f"1. '사과' 질문 -> {choice1} (기대값: process_red_fruit) -> {'✅ 일치' if choice1 == 'process_red_fruit' else '❌ 불일치'}")
    print(f"2. '바나나' 질문 -> {choice2} (기대값: process_yellow_fruit) -> {'✅ 일치' if choice2 == 'process_yellow_fruit' else '❌ 불일치'}")
    print("-" * 70)
    print("결론: 에이전트는 파이썬 코드가 아니라 '독스트링'을 읽고 판단합니다.")

if __name__ == "__main__":
    asyncio.run(main())
