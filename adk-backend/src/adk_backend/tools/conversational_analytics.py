from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from google.cloud import geminidataanalytics
from google.cloud import datacatalog_v1
from google.auth import default

from ..config import get_settings
from .reasoning_tracker import ReasoningTracker

_settings = get_settings()
DEFAULT_PROJECT_ID = _settings.google_project_id
DEFAULT_DATASET_ID = (
    _settings.bigquery_default_dataset
    or _settings.bigquery_dataset
    or "divorce_analytics"
)
logger = logging.getLogger(__name__)


# @tool 데코레이터 재사용 (bigquery.py와 동일)
def tool(description: str = "", **kwargs):
    """Google ADK FunctionTool을 위한 데코레이터"""
    def decorator(func):
        func._is_adk_tool = True
        func._tool_description = description
        func._tool_kwargs = kwargs
        return func
    return decorator


@tool(
    name="conversational.ask_insights",
    description="자연어 질문으로 BigQuery 데이터 인사이트를 생성합니다."
)
def ask_data_insights(
    question: str,
    table_names: Optional[str] = None,
) -> str:
    """
    자연어 질문으로 BigQuery 데이터 인사이트 생성.

    Args:
        question: 자연어 질문 (예: "지난 7일간 가장 많은 위협은?")
        table_names: 분석할 테이블 목록 (쉼표 구분, optional)

    Returns:
        JSON 문자열 형태의 AI 생성 인사이트
    """
    try:
        # 🚨 환경 변수 및 설정 확인
        import os
        logger.info("=" * 80)
        logger.info("🔧 Conversational Analytics - 환경 설정 확인")
        logger.info("=" * 80)
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
        logger.info(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
        logger.info(f"Settings - google_project_id: {_settings.google_project_id}")
        logger.info(f"Settings - bigquery_default_dataset: {_settings.bigquery_default_dataset}")
        logger.info(f"Settings - bigquery_location: {getattr(_settings, 'bigquery_location', 'N/A')}")
        logger.info("=" * 80)

        # 🧠 추론 추적 시작
        tracker = ReasoningTracker()

        # 서비스 계정 인증
        credentials, _ = default()
        logger.info(f"✅ 인증 성공: {type(credentials).__name__}")

        # 클라이언트 생성
        client = geminidataanalytics.DataChatServiceClient(
            credentials=credentials
        )

        # 프로젝트 정보
        project_id = DEFAULT_PROJECT_ID
        dataset_id = DEFAULT_DATASET_ID

        # 1단계: 질문 분석
        intent = _analyze_question_intent(question)
        required_data_types = _identify_required_data(question)

        tracker.add_question_analysis(
            question=question,
            intent=intent,
            required_data=required_data_types
        )

        # 테이블 목록 파싱 및 선정
        if not table_names:
            # 기본 테이블들 (이혼 판례 분석 전용)
            all_available_tables = [
                "precedent_cases",  # ✅ 핵심 판례 데이터 (위자료, 재산분할 등)
                "divorce_case_metadata",
            ]
            tables, table_reasons = _select_relevant_tables(question, intent, all_available_tables)
        else:
            tables = [t.strip() for t in table_names.split(",")]
            table_reasons = {t: "사용자가 명시적으로 지정" for t in tables}

        # 2단계: 테이블 선정 추론
        tracker.add_table_selection(
            selected_tables=tables,
            reasons=table_reasons,
            alternatives_considered=None
        )

        # BigQuery 테이블 참조 생성
        bq_table_references = []
        def _resolve_table_reference(table_name: str) -> geminidataanalytics.BigQueryTableReference:
            parts = table_name.split(".")
            if len(parts) == 3:
                proj, dataset, table = parts
            elif len(parts) == 2:
                proj = project_id
                dataset, table = parts
            else:
                proj = project_id
                dataset = dataset_id
                table = parts[0]

            if not dataset:
                dataset = DEFAULT_DATASET_ID

            return geminidataanalytics.BigQueryTableReference(
                project_id=proj,
                dataset_id=dataset,
                table_id=table,
            )

        for table in tables:
            ref = _resolve_table_reference(table)
            bq_table_references.append(ref)

        # 데이터 소스 설정
        bq_refs = geminidataanalytics.BigQueryTableReferences(
            table_references=bq_table_references
        )
        datasource_refs = geminidataanalytics.DatasourceReferences(bq=bq_refs)

        # 데이터 컨텍스트 (stateless 대화용)
        context = geminidataanalytics.Context(
            datasource_references=datasource_refs
        )

        # 메시지 생성
        user_message = geminidataanalytics.UserMessage(text=question)
        message = geminidataanalytics.Message(user_message=user_message)

        # 요청 생성
        request = geminidataanalytics.ChatRequest(
            parent=f"projects/{project_id}/locations/global",
            messages=[message],
            inline_context=context,
        )

        # 3단계: 쿼리 전략 추론
        strategy_type, operations = _infer_query_strategy(question, intent)
        tracker.add_query_strategy(
            strategy_type=strategy_type,
            operations=operations,
            rationale=f"{intent}를 위해 {strategy_type} 전략 사용"
        )

        # 🚨 실제 API 호출 확인용 로그
        logger.info("=" * 60)
        logger.info("🔥 REAL API CALL - Google Gemini Data Analytics API")
        logger.info("=" * 60)
        logger.info(f"Question: {question}")
        logger.info(f"Tables: {tables}")
        logger.info(f"Project: {project_id}")
        logger.info(f"Dataset: {dataset_id}")
        logger.info("API 호출 시작... (앵무새 아님!)")

        # 스트리밍 응답 처리
        response_text = ""
        generated_sql = None

        stream = client.chat(request=request)
        logger.info("📡 Streaming response from Google API...")
        for response in stream:
            if hasattr(response, 'agent_message') and response.agent_message.text:
                response_text += response.agent_message.text

            # SQL 쿼리 추출 (있다면)
            if hasattr(response, 'agent_message') and hasattr(response.agent_message, 'generated_sql'):
                generated_sql = response.agent_message.generated_sql

        # 🚨 API 응답 확인용 로그
        logger.info("=" * 60)
        logger.info("✅ API Response Received")
        logger.info("=" * 60)
        logger.info(f"Response length: {len(response_text)} characters")
        logger.info(f"Has SQL: {generated_sql is not None}")
        if generated_sql:
            logger.info(f"SQL preview: {generated_sql[:200]}...")
        logger.info(f"Response preview: {response_text[:300]}...")
        logger.info("=" * 60)

        # 4단계: 인사이트 도출 추론
        if response_text:
            findings_preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
            tracker.add_insight_derivation(
                findings=findings_preview,
                interpretation="Google Gemini API가 데이터 분석 및 인사이트 생성 완료",
                confidence=0.9
            )

        # 추론 결과 포맷팅
        formatted_reasoning = tracker.get_formatted_reasoning()
        reasoning_summary = tracker.get_summary_list()
        reasoning_detail = tracker.to_dict()

        logger.info(f"🧠 Reasoning steps generated: {len(tracker.steps)} steps")

        result = {
            "question": question,
            "tables_analyzed": tables,
            "insight": response_text,
            "generated_sql": generated_sql,
            "reasoning": reasoning_summary,
            "reasoning_detail": reasoning_detail,
            "reasoning_formatted": formatted_reasoning,
            "analysis_method": "conversational_analytics_api_v2",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ API Call Failed")
        logger.error("=" * 60)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("=" * 60)

        error_result = {
            "error": str(e),
            "error_type": type(e).__name__,
            "question": question,
            "is_real_api_error": True,  # 실제 API 호출 중 에러 발생
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool(
    name="conversational.search_catalog",
    description="BigQuery 카탈로그에서 테이블/뷰/모델을 검색합니다."
)
def search_catalog(
    query: str,
    max_results: Optional[int] = 20,
) -> str:
    """
    BigQuery 카탈로그에서 테이블/뷰/모델 검색.

    Args:
        query: 검색 쿼리 (예: "보안", "전환")
        max_results: 최대 결과 개수 (기본값: 20)

    Returns:
        JSON 문자열 형태의 검색된 리소스 목록
    """
    try:
        credentials, _ = default()
        client = datacatalog_v1.DataCatalogClient(credentials=credentials)

        project_id = _settings.google_project_id

        # 검색 범위 설정
        scope = datacatalog_v1.SearchCatalogRequest.Scope(
            include_project_ids=[project_id]
        )

        # 검색 실행
        search_request = datacatalog_v1.SearchCatalogRequest(
            scope=scope,
            query=query,
            page_size=max_results,
        )

        results = []
        for result in client.search_catalog(request=search_request):
            results.append({
                "name": result.relative_resource_name,
                "type": result.search_result_type.name,
                "linked_resource": result.linked_resource if hasattr(result, "linked_resource") else "",
            })

        catalog_result = {
            "query": query,
            "result_count": len(results),
            "resources": results,
        }

        return json.dumps(catalog_result, ensure_ascii=False, indent=2)

    except Exception as e:
        error_result = {
            "error": str(e),
            "query": query,
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


# 🧠 추론 헬퍼 함수들
def _analyze_question_intent(question: str) -> str:
    """질문의 의도를 분석"""
    question_lower = question.lower()

    # 의도 패턴 매칭
    if any(keyword in question_lower for keyword in ["건수", "수", "개수", "몇", "얼마나"]):
        return "데이터 집계 및 카운팅"
    elif any(keyword in question_lower for keyword in ["가장", "최고", "최대", "최소", "top"]):
        return "순위 및 극값 분석"
    elif any(keyword in question_lower for keyword in ["비교", "차이", "vs", "대비"]):
        return "비교 분석"
    elif any(keyword in question_lower for keyword in ["추세", "변화", "트렌드", "추이"]):
        return "시계열 트렌드 분석"
    elif any(keyword in question_lower for keyword in ["전환", "전환율", "conversion"]):
        return "전환율 및 퍼널 분석"
    elif any(keyword in question_lower for keyword in ["평균", "중앙값", "분포"]):
        return "통계 분석"
    else:
        return "일반 데이터 조회"


def _identify_required_data(question: str) -> List[str]:
    """질문에 필요한 데이터 타입 식별"""
    question_lower = question.lower()
    required_data = []

    # 도메인별 키워드 매핑 (이혼 판례 도메인)
    if any(keyword in question_lower for keyword in ["위자료", "alimony", "금액", "보상"]):
        required_data.append("위자료 통계 데이터 (precedent_cases.alimony_amount)")
    if any(keyword in question_lower for keyword in ["재산", "분할", "property", "ratio", "비율"]):
        required_data.append("재산분할 통계 데이터 (precedent_cases.property_ratio_plaintiff)")
    if any(keyword in question_lower for keyword in ["유책", "사유", "fault", "부정행위", "외도", "폭언"]):
        required_data.append("이혼 사유별 판례 데이터 (precedent_cases.fault_type)")
    if any(keyword in question_lower for keyword in ["태그", "검색", "tags"]):
        required_data.append("판례 검색 태그 (precedent_cases.tags)")

    # 시간 관련
    if any(keyword in question_lower for keyword in ["일", "주", "월", "년", "기간", "날짜", "선고"]):
        required_data.append("선고 시점 정보 (judgment_date)")

    return required_data if required_data else ["일반 판례 데이터"]


def _select_relevant_tables(
    question: str,
    intent: str,
    available_tables: List[str]
) -> tuple[List[str], Dict[str, str]]:
    """질문과 의도에 기반하여 관련 테이블 선택"""
    question_lower = question.lower()
    selected = []
    reasons = {}

    # 테이블별 키워드 매핑 (이혼 판례 도메인)
    table_keywords = {
        "precedent_cases": {
            "keywords": ["판례", "위자료", "재산", "분할", "유책", "사유", "부정행위", "금액", "비율", "건수", "통계"],
            "reason": "핵심 이혼 판례 데이터 (위자료, 재산분할비율, 유책사유 등 포함)"
        },
        "divorce_case_metadata": {
            "keywords": ["메타", "데이터", "관리"],
            "reason": "판례 문서 메타데이터 정보"
        }
    }

    # 키워드 기반 테이블 선택
    for table in available_tables:
        if table in table_keywords:
            config = table_keywords[table]
            if any(keyword in question_lower for keyword in config["keywords"]):
                selected.append(table)
                reasons[table] = config["reason"]

    # 선택된 테이블이 없으면 기본 테이블 사용
    if not selected:
        selected = ["precedent_cases"]
        reasons = {
            "precedent_cases": "기본 이혼 판례 통계 데이터"
        }

    return selected, reasons


def _infer_query_strategy(question: str, intent: str) -> tuple[str, List[str]]:
    """질문과 의도에서 쿼리 전략 추론"""
    question_lower = question.lower()
    operations = []

    # 의도별 전략
    if "집계" in intent or "카운팅" in intent:
        strategy = "집계 쿼리 (Aggregation)"
        operations = ["COUNT() 함수로 건수 집계"]
    elif "순위" in intent or "극값" in intent:
        strategy = "순위 쿼리 (Ranking)"
        operations = ["ORDER BY로 정렬", "LIMIT로 상위/하위 추출"]
    elif "비교" in intent:
        strategy = "비교 쿼리 (Comparison)"
        operations = ["GROUP BY로 그룹화", "비교 메트릭 계산"]
    elif "트렌드" in intent:
        strategy = "시계열 쿼리 (Time Series)"
        operations = ["날짜별 GROUP BY", "시간 순서 정렬"]
    elif "전환" in intent:
        strategy = "퍼널 분석 (Funnel Analysis)"
        operations = ["이벤트 조인", "전환율 계산"]
    elif "통계" in intent:
        strategy = "통계 쿼리 (Statistical)"
        operations = ["AVG(), MEDIAN() 등 통계 함수", "분포 계산"]
    else:
        strategy = "일반 SELECT 쿼리"
        operations = ["기본 데이터 조회"]

    # 시간 필터링 감지
    if any(keyword in question_lower for keyword in ["지난", "최근", "이번", "작년"]):
        operations.append("날짜 필터링 (WHERE date >= ...)")

    # 조건 필터링 감지
    if any(keyword in question_lower for keyword in ["등급", "타입", "유형", "종류"]):
        operations.append("조건 필터링 (WHERE type = ...)")

    return strategy, operations
