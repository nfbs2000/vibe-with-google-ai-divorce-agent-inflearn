"""
File Search Tool 통합 테스트

실제 Gemini File Search API를 사용한 통합 테스트
"""
from __future__ import annotations

import os

import pytest

from adk_backend.tools.file_search import (
    FileSearchTool,
    get_file_search_tool,
    search_documents,
)


def test_file_search_tool_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    """API Key 없으면 에러"""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("FILE_SEARCH_STORE_NAME", raising=False)

    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        FileSearchTool()


def test_file_search_tool_requires_store_name(monkeypatch: pytest.MonkeyPatch):
    """Store Name 없으면 에러"""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    monkeypatch.delenv("FILE_SEARCH_STORE_NAME", raising=False)

    with pytest.raises(ValueError, match="FILE_SEARCH_STORE_NAME"):
        FileSearchTool()


def test_file_search_tool_initialization():
    """FileSearchTool 초기화 성공"""
    # 환경 변수가 설정되어 있다고 가정
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool = FileSearchTool()

    assert tool.api_key == api_key
    assert tool.store_name == store_name
    assert tool.model == "gemini-2.5-flash"
    assert tool.client is None  # Lazy initialization


def test_file_search_tool_custom_model():
    """커스텀 모델 설정"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool = FileSearchTool(model="gemini-3-pro-preview-11-2025")

    assert tool.model == "gemini-3-pro-preview-11-2025"


@pytest.mark.integration
def test_file_search_real_query():
    """실제 File Search 쿼리 테스트"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool = FileSearchTool()
    result = tool.search("ADK에서 sub-agent를 어떻게 만들어?", max_results=3)

    # 결과 검증
    assert "answer" in result
    assert result["answer"]  # 답변이 비어있지 않음
    assert "citations" in result
    assert "model" in result
    assert "error" not in result

    # 로그 출력
    print(f"\n질문: ADK에서 sub-agent를 어떻게 만들어?")
    print(f"답변: {result['answer'][:200]}...")
    print(f"Citations: {len(result['citations'])}개")


@pytest.mark.integration
def test_file_search_with_citations():
    """실제 Citations 포함 검색 테스트"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool = FileSearchTool()
    result = tool.search("transfer_to_agent", max_results=5, include_citations=True)

    # Citations 검증
    assert len(result["citations"]) > 0, "Citations가 반환되어야 함"

    # 첫 번째 citation 구조 확인
    first_citation = result["citations"][0]
    assert "source" in first_citation or "content" in first_citation

    # 로그 출력
    print(f"\n질문: transfer_to_agent")
    print(f"답변: {result['answer'][:200]}...")
    print(f"Citations: {len(result['citations'])}개")
    for i, citation in enumerate(result["citations"][:3], 1):
        print(f"  {i}. {citation.get('source', 'N/A')}: {citation.get('content', '')[:100]}...")


@pytest.mark.integration
def test_file_search_multiple_queries():
    """여러 쿼리 연속 테스트"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool = FileSearchTool()

    queries = [
        "Agent란 무엇인가?",
        "Memory Bank 사용법",
        "Session 관리",
    ]

    for query in queries:
        result = tool.search(query, max_results=2)
        assert "answer" in result
        assert result["answer"]
        print(f"\n질문: {query}")
        print(f"답변: {result['answer'][:150]}...")


def test_file_search_tool_singleton():
    """get_file_search_tool은 싱글톤"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool1 = get_file_search_tool()
    tool2 = get_file_search_tool()

    assert tool1 is tool2


def test_format_response():
    """format_response 포맷팅 테스트"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool = FileSearchTool()

    result = {
        "answer": "ADK는 Agent Development Kit입니다.",
        "citations": [
            {
                "source": "index.md",
                "content": "ADK (Agent Development Kit) is a toolkit for building AI agents..."
            }
        ],
        "model": "gemini-2.5-flash"
    }

    formatted = tool.format_response(result)

    assert "ADK는 Agent Development Kit입니다." in formatted
    assert "📚 **출처**:" in formatted
    assert "index.md" in formatted
