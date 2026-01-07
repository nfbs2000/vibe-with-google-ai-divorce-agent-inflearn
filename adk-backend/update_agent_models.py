#!/usr/bin/env python3
"""
모든 ADK 에이전트의 하드코딩된 모델을 환경 변수 기반으로 변경
"""
import re
from pathlib import Path

# 수정할 파일 목록
agent_files = [
    "src/adk_backend/agents/security_domain_expert.py",
    "src/adk_backend/agents/audio_analytics_domain_expert.py",
    "src/adk_backend/agents/security_intelligence_agent.py",
    "src/adk_backend/agents/marketing_domain_expert.py",
    "src/adk_backend/agents/infrastructure_agent.py",
    "src/adk_backend/agents/antigravity_dev_sec_ops_expert.py",
    "src/adk_backend/agents/conversion_domain_expert.py",
    "src/adk_backend/agents/alyac_family_domain_expert.py",
    "src/adk_backend/agents/base/conversational_analytics_agent.py",
]

BASE_DIR = Path(__file__).parent

for file_path in agent_files:
    full_path = BASE_DIR / file_path
    if not full_path.exists():
        print(f"⚠️  파일 없음: {file_path}")
        continue

    print(f"📝 수정 중: {file_path}")

    # 파일 읽기
    content = full_path.read_text(encoding='utf-8')

    # import 문 추가 (이미 있으면 중복 안됨)
    if 'from ...config import get_settings' not in content and 'from ..config import get_settings' not in content and 'from .config import get_settings' not in content:
        # import 위치 찾기
        import_section_match = re.search(r'(from google\.(adk|genai)\.[^\n]+\n)', content)
        if import_section_match:
            import_end = import_section_match.end()
            # import 경로 결정 (파일 depth에 따라)
            if '/base/' in file_path:
                import_line = '\nfrom ...config import get_settings\n'
            else:
                import_line = '\nfrom ..config import get_settings\n'

            content = content[:import_end] + import_line + content[import_end:]

    # settings 로드 코드 추가 (Agent 정의 전에)
    if 'settings = get_settings()' not in content:
        # Agent 정의 찾기
        agent_def_match = re.search(r'\n([a-z_]+_agent = Agent\()', content)
        if agent_def_match:
            agent_def_start = agent_def_match.start()
            settings_code = '\n# ADK 모델 설정 로드\nsettings = get_settings()\n'
            content = content[:agent_def_start] + settings_code + content[agent_def_start:]

    # model="gemini-2.5-flash" 또는 model="gemini-2.0-flash-exp" -> model=settings.adk_model_name
    content = re.sub(
        r'model="gemini-[^"]+",',
        'model=settings.adk_model_name,',
        content
    )

    # 파일 쓰기
    full_path.write_text(content, encoding='utf-8')
    print(f"✅ 완료: {file_path}")

print("\n🎉 모든 에이전트 파일 수정 완료!")
