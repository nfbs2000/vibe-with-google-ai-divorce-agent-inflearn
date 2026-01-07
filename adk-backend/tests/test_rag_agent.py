"""
RAG Agent 통합 테스트

실제 Gemini File Search를 활용한 RAG Agent 테스트
"""
from __future__ import annotations

import os

import pytest

# Set required environment variable before importing agents
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")

# Skip all tests if ADK is not installed
pytest.importorskip("google.genai.adk")

from adk_backend.agents.rag_agent import rag_agent
from adk_backend.agents.registry import AGENT_REGISTRY, get_agent_info


def test_rag_agent_exists():
    """RAG Agent가 정의되어 있음"""
    assert rag_agent is not None
    assert rag_agent.name == "rag_analyst"


def test_rag_agent_has_search_tool():
    """RAG Agent가 search_documents tool을 가지고 있음"""
    tool_names = [tool.name for tool in rag_agent.tools]
    assert "search_documents" in tool_names


def test_rag_agent_in_registry():
    """RAG Agent가 registry에 등록되어 있음"""
    assert "rag" in AGENT_REGISTRY

    rag_info = AGENT_REGISTRY["rag"]
    assert rag_info.key == "rag"
    assert rag_info.display_name == "RAG 문서 검색가"
    assert rag_info.agent is rag_agent
    assert rag_info.active is True


def test_rag_agent_keywords():
    """RAG Agent 키워드 확인"""
    rag_info = get_agent_info("rag")

    expected_keywords = ["문서", "검색", "rag", "파일", "질문", "답변"]
    for keyword in expected_keywords:
        assert keyword in rag_info.keywords


def test_rag_agent_strengths():
    """RAG Agent 강점 확인"""
    rag_info = get_agent_info("rag")

    assert len(rag_info.strengths) > 0
    assert any("Gemini File Search" in strength for strength in rag_info.strengths)
    assert any("Citation" in strength or "출처" in strength for strength in rag_info.strengths)


def test_rag_agent_focus():
    """RAG Agent focus 영역 확인"""
    rag_info = get_agent_info("rag")

    assert rag_info.focus == "문서 검색 및 RAG"


def test_rag_agent_description():
    """RAG Agent 설명 확인"""
    rag_info = get_agent_info("rag")

    assert "Gemini File Search" in rag_info.description
    assert "문서 검색" in rag_info.description


def test_rag_agent_instruction_quality():
    """RAG Agent instruction 품질 확인"""
    instruction = rag_agent.instruction

    # 주요 역할이 명시되어 있는지
    assert "문서 검색" in instruction or "RAG" in instruction

    # File Search 도구 사용이 명시되어 있는지
    assert "search_documents" in instruction or "File Search" in instruction

    # Citation 중요성이 명시되어 있는지
    assert "Citation" in instruction or "출처" in instruction

    # 응답 형식 가이드가 있는지
    assert "응답 형식" in instruction or "응답" in instruction


def test_rag_agent_has_memory_service():
    """RAG Agent가 memory service를 가지고 있음"""
    assert rag_agent.memory_service is not None


def test_rag_agent_model_from_config():
    """RAG Agent가 config에서 모델을 로드함"""
    from adk_backend.config import get_settings

    settings = get_settings()

    # RAG agent의 모델은 settings.adk_model_name과 같아야 함
    assert rag_agent.model == settings.adk_model_name


@pytest.mark.parametrize(
    "keyword",
    [
        "문서",
        "검색",
        "rag",
        "파일",
        "질문",
        "답변",
        "지식",
        "리포트",
        "분석문서",
        "기술문서",
        "매뉴얼",
        "가이드",
        "참조",
        "citation",
        "출처",
    ],
)
def test_rag_agent_all_keywords_present(keyword):
    """RAG Agent의 모든 키워드가 registry에 있음"""
    rag_info = get_agent_info("rag")
    assert keyword in rag_info.keywords


def test_rag_agent_instruction_structure():
    """RAG Agent instruction 구조 확인"""
    instruction = rag_agent.instruction

    # 주요 섹션이 있는지 확인
    expected_sections = [
        "주요 역할",
        "검색",
        "응답 형식",
        "중요 지침",
    ]

    for section in expected_sections:
        assert section in instruction, f"'{section}' 섹션이 instruction에 없습니다"


def test_rag_agent_tool_count():
    """RAG Agent가 적절한 수의 tool을 가지고 있음"""
    # RAG agent는 search_documents만 가져야 함 (단순하게)
    assert len(rag_agent.tools) == 1
    assert rag_agent.tools[0].name == "search_documents"


def test_rag_agent_no_sub_agents():
    """RAG Agent는 sub-agent를 가지지 않음"""
    # RAG agent는 단순 검색 도구이므로 sub-agent 불필요
    assert len(rag_agent.sub_agents) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_agent_real_search():
    """실제 RAG Agent로 ADK 문서 검색 테스트"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    # RAG Agent에게 질문
    from google.genai.adk import Agent

    query = "ADK에서 sub-agent를 어떻게 만들어?"

    # Agent의 run 메서드 사용
    response = await rag_agent.run_async(query)

    # 응답 검증
    assert response is not None
    print(f"\n질문: {query}")
    print(f"RAG Agent 응답: {response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_agent_multiple_queries():
    """RAG Agent로 여러 질문 연속 테스트"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    queries = [
        "Memory Bank란 무엇인가?",
        "Session 관리 방법은?",
        "Tool 사용법은?",
    ]

    for query in queries:
        response = await rag_agent.run_async(query)
        assert response is not None
        print(f"\n질문: {query}")
        print(f"RAG Agent 응답 길이: {len(str(response))} 문자")
