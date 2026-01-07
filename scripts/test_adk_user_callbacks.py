#!/usr/bin/env python3
"""
[ADK 심화 예제] 사용자 정의 콜백(Callbacks) - 보안, 프라이버시, 비용 제어
----------------------------------------------------------------------
"""
import sys
import os
import asyncio
import re
from typing import Any, Dict
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
    print("❌ ImportError", flush=True)
    sys.exit(1)

# === 🛡️ 1. 보안 콜백 구현 (Tool Wrapper) ===
def secure_read_file(file_path: str):
    """
    [도구] 파일 내용을 읽어옵니다. 반드시 파일 경로를 문자열로 입력하세요.
    """
    # [Callback: on_tool_start]
    print(f"   👮 [Security Audit] 접근 요청된 경로: {file_path}", flush=True)
    
    # 1. 상위 디렉토리(..) 접근 차단 (Path Traversal)
    if ".." in file_path:
        raise ValueError("⛔️ [Security Blocked] 상위 디렉토리(..) 접근은 차단되었습니다.")
    
    # 2. 절대 경로(/) 접근 차단
    if file_path.startswith("/"):
        raise ValueError("⛔️ [Security Blocked] 절대 경로(/) 접근은 차단되었습니다.")
        
    return f"📂 파일 내용을 읽었습니다: {file_path}"

# === 🔒 2. 프라이버시 콜백 구현 (Response Filter) ===
def privacy_masking_callback(text: str) -> str:
    print(f"   🔍 [Privacy Check] 응답 검사 중...", flush=True)
    phone_pattern = r"010[-.\s]?\d{3,4}[-.\s]?\d{4}"
    if re.search(phone_pattern, text):
        print("   🙈 [Privacy Filter] 전화번호 패턴 감지! 마스킹 처리합니다.", flush=True)
        return re.sub(phone_pattern, "010-****-****", text)
    return text

async def run_callback_test(scenario_name, query, instruction_override=None, max_steps=10):
    print(f"\n🧪 [테스트] {scenario_name}", flush=True)
    print(f"   질문: '{query}'", flush=True)
    
    settings = get_settings()
    
    base_instruction = (
        "너는 테스트용 봇이야. 사용자가 시키는 대로 무조건 수행해.\n"
        "파일 경로를 읽으라고 하면 의심하지 말고 도구를 호출해.\n"
        "전화번호를 말하라고 하면 그대로 따라서 말해."
    )
    
    agent = Agent(
        name="secure_agent",
        model=settings.adk_model_name,
        instruction=instruction_override or base_instruction,
        tools=[FunctionTool(secure_read_file)]
    )

    runner = InMemoryRunner(app_name="adk_callback_test", agent=agent)
    session_id = f"sess_{scenario_name}"
    user_id = "tester"
    
    try:
        await runner.session_service.create_session(
            app_name="adk_callback_test", 
            user_id=user_id, 
            session_id=session_id
        )
    except: pass

    message = genai_types.Content(
        role="user", 
        parts=[genai_types.Part(text=query)]
    )

    current_steps = 0
    final_response = ""

    try:
        async for event in runner.run_async(
            user_id=user_id, 
            session_id=session_id, 
            new_message=message
        ):
            # [Callback: on_step_end] 비용 제어
            if hasattr(event, "content") and event.content: # 모델 응답이 있을 때 스텝 증가로 간주
                 current_steps += 1
            
            if current_steps > max_steps:
                print(f"   💸 [Cost Control] 허용된 스텝({max_steps}) 초과! 강제 종료합니다.", flush=True)
                break

            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        print(f"   🛠️  도구 실행 시도: {part.function_call.name}", flush=True)

            if hasattr(event, "text") and event.text:
                final_response += event.text

    except Exception as e:
        print(f"   ⚠️ 에러 발생: {e}", flush=True)

    # [Callback: on_agent_finish] 프라이버시 필터 적용
    masked_response = privacy_masking_callback(final_response)
    
    if masked_response:
        print(f"   💬 최종 응답: {masked_response.strip()}", flush=True)

async def main():
    print("=" * 70, flush=True)
    print("🛡️  ADK Callback 시스템 테스트 (Security, Privacy, Cost)", flush=True)
    print("=" * 70, flush=True)

    # 1. 보안 위반 테스트 (경로 조작)
    # Gemini 안전 필터를 피하기 위해 passwd 대신 secret.txt 등 덜 위험한 이름 사용
    await run_callback_test(
        "Security_Breach", 
        "파일 '../secret_plans.txt'를 읽어줘. 상대 경로를 그대로 사용해."
    )

    # 2. 개인정보 보호 테스트
    await run_callback_test(
        "Privacy_Leak", 
        "내 번호는 010-9999-8888이야. '확인되었습니다: [번호]' 라고 답변해."
    )

    # 3. 비용 제어 테스트 (Max Step=1 -> 2번째 턴에서 종료)
    await run_callback_test(
        "Cost_Limit", 
        "이 파일을 읽고, 그 내용을 다시 읽고 반복해.", 
        max_steps=1
    )

if __name__ == "__main__":
    asyncio.run(main())
