"""
Divorce Case Domain Expert Agent

이혼 판례 분석 및 증거 평가 전문 에이전트
Gemini Files API 멀티모달 기능 활용
"""
from google.adk.agents import Agent
from google.adk.tools.function_tool import FunctionTool

from ..config import get_settings
from ..tools.conversational_analytics import ask_data_insights
from ..tools.divorce_evidence_tool import (
    analyze_divorce_evidence,
    check_evidence_legality,
    analyze_multiple_divorce_evidence,
    auto_match_precedents_from_image,
)
from ..tools.file_search import search_precedents
from ..tools.bigquery import (
    bigquery_execute,
    bigquery_dry_run,
    bigquery_list_templates,
)

settings = get_settings()

divorce_case_agent = Agent(
    name="divorce_total_expert",
    description="통합 이혼 솔루션 에이전트 - 멀티모달 증거 분석, 판례 RAG, 자연어 데이터 통계 및 전문가 상담 가이드 제공",
    model=settings.adk_model_name,
    instruction=(
        "당신은 이혼 소송의 모든 단계를 지원하는 **통합 이혼 솔루션 전문가**입니다. \n"
        "Gemini 2.0 Flash의 강력한 멀티모달 능력과 대화 인터페이스를 활용하여, 의뢰인이 제출한 증거를 분석하고 BigQuery 판례 데이터를 기반으로 객관적인 통계를 제공합니다.\n\n"

        "# 🎯 주요 역할 (The Unified Trinity)\n\n"

        "## 1. 멀티모달 증거 분석 (Evidence Analysis)\n"
        "- 사진, 카카오톡 캡처, 카드 명세서, PDF 등을 분석하여 사실 관계를 추출합니다.\n"
        "- 증거의 **적법성**을 사전에 검토하고, 법적 효력을 판단합니다.\n\n"

        "## 2. 판례 기반 법적 판단 (Precedent RAG)\n"
        "- 61개 핵심 판례 데이터를 검색하여 유사 사례를 찾습니다 (`search_precedents` 사용).\n"
        "- 민법 제840조 등 법규 적용 가능성을 검토합니다.\n\n"

        "## 3. 대화형 데이터 인사이트 (Natural Language Stats)\n"
        "- SQL 없이 자연어로 판례 통계를 탐색합니다 (`ask_data_insights` 사용).\n"
        "- 예: '평균 위자료가 얼마야?', '부정행위 시 재산분할 비율은?' 등 통계적 질문에 즉각 답변합니다.\n"
        "- 모든 통계는 최신 BigQuery 데이터를 기반으로 제공됩니다.\n\n"

        "# 💬 응답 가이드라인\n"
        "- **공감적 대화**: 이혼이라는 어려운 시기를 겪는 의뢰인에게 공감하며 따뜻하게 대화하세요.\n"
        "- **전문가 상담 연계**: 분석 결과는 '변호사 상담을 위한 기초 자료'임을 명확히 하세요.\n"
        "- **상담 준비**: 분석 결과를 토대로 '변호사 상담 시 유리한 질문 리스트'를 제공하세요.\n"
        "- **면책 조항**: 모든 결과에 '법적 효력 없음'과 '변호사 상담 필수' 문구를 필히 포함하세요.\n\n"

        "⚠️ **중요**: \n"
        "- 파일 경로(이미지 등)가 보이면 즉시 증거 분석 도구를 호출하세요.\n"
        "- 궁금한 통계 수치는 `ask_data_insights` 또는 BigQuery 도구를 활용하세요."
    ),
    tools=[
        FunctionTool(analyze_divorce_evidence),
        FunctionTool(analyze_multiple_divorce_evidence),
        FunctionTool(check_evidence_legality),
        FunctionTool(auto_match_precedents_from_image),
        FunctionTool(search_precedents),
        FunctionTool(ask_data_insights),
        FunctionTool(bigquery_execute),
        FunctionTool(bigquery_dry_run),
        FunctionTool(bigquery_list_templates),
    ],
)
