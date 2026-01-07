"""
File Search 검증 테스트

실제 인덱스된 ADK 문서와 File Search 결과가 일치하는지 검증
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from adk_backend.tools.file_search import FileSearchTool


# Ground truth 파일 경로
GROUND_TRUTH_FILE = Path(__file__).parent / "fixtures" / "adk_ground_truth.json"
RESULTS_FILE = Path(__file__).parent / "fixtures" / "verification_results.json"


def load_ground_truth():
    """Ground truth 데이터 로드"""
    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_verification_results(results: dict):
    """검증 결과 저장"""
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def check_keywords(answer: str, keywords: list[str]) -> tuple[bool, list[str]]:
    """
    답변에 예상 키워드가 포함되어 있는지 확인

    Returns:
        (전체 통과 여부, 찾은 키워드 리스트)
    """
    answer_lower = answer.lower()
    found_keywords = []

    for keyword in keywords:
        if keyword.lower() in answer_lower:
            found_keywords.append(keyword)

    # 최소 50% 이상의 키워드가 있어야 통과
    pass_threshold = len(keywords) * 0.5
    passed = len(found_keywords) >= pass_threshold

    return passed, found_keywords


@pytest.mark.integration
@pytest.mark.slow
def test_file_search_model_info():
    """File Search에서 사용하는 모델 정보 확인"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool = FileSearchTool()

    # 모델 정보 출력
    print(f"\n📊 File Search Tool 모델 정보:")
    print(f"  - Generation Model: {tool.model}")
    print(f"  - Store Name: {tool.store_name}")
    print(f"  - API Key: {'설정됨' if tool.api_key else '없음'}")

    # 모델이 설정되어 있는지 확인
    assert tool.model in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]


@pytest.mark.integration
@pytest.mark.slow
def test_ground_truth_verification():
    """
    Ground truth 기반 검증 테스트

    실제 인덱스된 ADK 문서를 검색하여 예상 키워드와 일치하는지 확인
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    # Ground truth 로드
    ground_truth = load_ground_truth()
    test_cases = ground_truth["test_cases"]

    tool = FileSearchTool()

    results = {
        "timestamp": datetime.now().isoformat(),
        "model": tool.model,
        "store_name": tool.store_name,
        "total_cases": len(test_cases),
        "passed_cases": 0,
        "failed_cases": 0,
        "test_results": []
    }

    print(f"\n🔍 Ground Truth 검증 시작 (총 {len(test_cases)}개 케이스)")
    print(f"📦 File Search Store: {store_name}")
    print(f"🤖 Generation Model: {tool.model}\n")

    for test_case in test_cases:
        test_id = test_case["id"]
        question = test_case["question"]
        expected_keywords = test_case["expected_keywords"]

        print(f"\n{'='*80}")
        print(f"📝 Test Case: {test_id}")
        print(f"❓ Question: {question}")

        # File Search 실행
        search_result = tool.search(question, max_results=5, include_citations=True)

        if "error" in search_result:
            print(f"❌ Search Error: {search_result['error']}")
            results["failed_cases"] += 1
            results["test_results"].append({
                "test_id": test_id,
                "question": question,
                "status": "error",
                "error": search_result["error"]
            })
            continue

        answer = search_result["answer"]
        citations = search_result["citations"]

        # 키워드 검증
        passed, found_keywords = check_keywords(answer, expected_keywords)

        print(f"💬 Answer: {answer[:200]}...")
        print(f"🔑 Expected Keywords: {expected_keywords}")
        print(f"✅ Found Keywords: {found_keywords}")
        print(f"📚 Citations: {len(citations)}개")

        if citations:
            for i, citation in enumerate(citations[:3], 1):
                print(f"  {i}. {citation.get('source', 'N/A')}")

        if passed:
            print(f"✅ PASSED")
            results["passed_cases"] += 1
        else:
            print(f"❌ FAILED (found {len(found_keywords)}/{len(expected_keywords)} keywords)")
            results["failed_cases"] += 1

        # 결과 저장
        results["test_results"].append({
            "test_id": test_id,
            "question": question,
            "answer": answer,
            "expected_keywords": expected_keywords,
            "found_keywords": found_keywords,
            "citations": [
                {
                    "source": c.get("source", ""),
                    "content_preview": c.get("content", "")[:100] + "..."
                    if "content" in c else ""
                }
                for c in citations
            ],
            "status": "passed" if passed else "failed",
            "keyword_match_rate": f"{len(found_keywords)}/{len(expected_keywords)}"
        })

    # 결과 요약
    print(f"\n{'='*80}")
    print(f"📊 검증 결과 요약:")
    print(f"  - 총 테스트: {results['total_cases']}개")
    print(f"  - 통과: {results['passed_cases']}개")
    print(f"  - 실패: {results['failed_cases']}개")
    print(f"  - 성공률: {results['passed_cases']/results['total_cases']*100:.1f}%")

    # 결과 파일 저장
    save_verification_results(results)
    print(f"\n💾 검증 결과 저장: {RESULTS_FILE}")

    # 최소 60% 이상 통과해야 전체 테스트 통과
    success_rate = results['passed_cases'] / results['total_cases']
    assert success_rate >= 0.6, f"성공률 {success_rate*100:.1f}%가 기준(60%) 미달"


@pytest.mark.integration
@pytest.mark.slow
def test_specific_adk_knowledge():
    """
    특정 ADK 지식 검증 (수동 확인용)

    알려진 ADK 개념들이 정확하게 검색되는지 확인
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool = FileSearchTool()

    # 알려진 사실들 테스트
    known_facts = {
        "sub_agents parameter": "ADK에서 sub-agent를 추가할 때 사용하는 파라미터는?",
        "Single Parent Rule": "ADK에서 한 agent를 여러 parent에 추가하면 어떻게 되나요?",
        "SequentialAgent": "ADK의 SequentialAgent는 무엇인가요?",
    }

    for fact_name, question in known_facts.items():
        result = tool.search(question, max_results=3)

        print(f"\n📌 {fact_name}")
        print(f"Q: {question}")
        print(f"A: {result['answer'][:300]}...")

        assert "error" not in result
        assert result["answer"]  # 답변이 있어야 함


@pytest.mark.integration
@pytest.mark.slow
def test_file_search_citation_quality():
    """Citation 품질 검증"""
    api_key = os.getenv("GOOGLE_API_KEY")
    store_name = os.getenv("FILE_SEARCH_STORE_NAME")

    if not api_key or not store_name:
        pytest.skip("GOOGLE_API_KEY and FILE_SEARCH_STORE_NAME required")

    tool = FileSearchTool()

    # 명확한 답이 있는 질문
    query = "ADK에서 agent hierarchy를 탐색하는 방법은?"
    result = tool.search(query, max_results=5, include_citations=True)

    print(f"\n질문: {query}")
    print(f"답변: {result['answer']}")
    print(f"\nCitations ({len(result['citations'])}개):")

    assert len(result["citations"]) > 0, "Citations가 반환되어야 함"

    for i, citation in enumerate(result["citations"], 1):
        print(f"\n{i}. Source: {citation.get('source', 'N/A')}")
        if "content" in citation:
            print(f"   Content: {citation['content'][:200]}...")

        # Citation 구조 검증
        assert "source" in citation or "content" in citation, "Citation은 source나 content를 포함해야 함"
