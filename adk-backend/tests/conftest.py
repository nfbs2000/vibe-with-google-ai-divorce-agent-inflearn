"""
Pytest 설정 파일

.env 파일 자동 로딩 및 테스트 환경 설정
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def load_env():
    """
    테스트 실행 전에 .env 파일 로드

    프로젝트 루트의 .env 파일을 자동으로 로드하여
    모든 테스트에서 환경 변수 사용 가능
    """
    # 프로젝트 루트 경로
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        load_dotenv(env_file)
        print(f"\n✅ Loaded .env from: {env_file}")
        print(f"   - GOOGLE_API_KEY: {'설정됨' if os.getenv('GOOGLE_API_KEY') else '없음'}")
        print(f"   - FILE_SEARCH_STORE_NAME: {os.getenv('FILE_SEARCH_STORE_NAME', '없음')}")
        print(f"   - GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', '없음')}")
    else:
        print(f"\n⚠️  .env file not found at: {env_file}")


@pytest.fixture(scope="session")
def check_integration_requirements():
    """
    통합 테스트 실행을 위한 요구사항 확인

    Returns:
        bool: 통합 테스트 실행 가능 여부
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("Integration tests require GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME")

    return True
