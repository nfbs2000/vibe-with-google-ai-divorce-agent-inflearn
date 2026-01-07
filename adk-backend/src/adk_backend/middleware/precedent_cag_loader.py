"""
Precedent CAG (Context-Augmented Generation) Loader

51개 판례 메타데이터를 BigQuery에서 로드하여 Gemini의 Context Cache용 CAG 생성
"""
import json
import logging
from typing import Optional, List, Dict, Any
from google.cloud import bigquery

logger = logging.getLogger(__name__)


class PrecedentCAGLoader:
    """
    판례 메타데이터 로더 (BigQuery 기반)

    BigQuery의 precedent_cases 테이블에서 51개 판례 메타데이터를 조회하여
    Gemini의 Context Cache용으로 포맷된 CAG를 생성합니다.
    서버 시작시 한 번만 로드되며, 모든 사용자가 같은 CAG를 공유합니다.
    """

    def __init__(self, project_id: Optional[str] = None, dataset_id: str = "divorce_analytics",
                 table_id: str = "precedent_cases"):
        """
        CAG 로더 초기화

        Args:
            project_id: BigQuery 프로젝트 ID (자동 감지)
            dataset_id: BigQuery 데이터셋 ID
            table_id: BigQuery 테이블 ID
        """
        self.bq_client = bigquery.Client()
        self.project_id = project_id or self.bq_client.project
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.cag_data: List[Dict[str, Any]] = []

    def load_metadata(self) -> bool:
        """
        BigQuery에서 판례 메타데이터 로드

        Returns:
            성공 여부
        """
        try:
            query = f"""
            SELECT
                case_id,
                case_number,
                fault_type,
                alimony_amount,
                property_ratio_plaintiff,
                marriage_duration_years,
                summary
            FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
            ORDER BY case_id
            """

            logger.info(f"BigQuery에서 판례 메타데이터 로드 중... ({self.project_id}.{self.dataset_id}.{self.table_id})")
            query_job = self.bq_client.query(query)
            rows = query_job.result()

            self.cag_data = []
            for row in rows:
                case_summary = {
                    "case_id": str(row.case_id) if row.case_id else "",
                    "case_number": str(row.case_number) if row.case_number else "",
                    "fault_type": str(row.fault_type) if row.fault_type else "Unknown",
                    "alimony_amount": int(row.alimony_amount) if row.alimony_amount else 0,
                    "property_ratio_plaintiff": float(row.property_ratio_plaintiff) if row.property_ratio_plaintiff else 0.0,
                    "marriage_duration_years": int(row.marriage_duration_years) if row.marriage_duration_years else -1,
                    "summary": str(row.summary)[:200] if row.summary else ""  # 요약만 포함 (토큰 절감)
                }
                self.cag_data.append(case_summary)

            logger.info(f"✅ BigQuery CAG 로드 완료: {len(self.cag_data)}개 판례")
            return len(self.cag_data) > 0

        except Exception as e:
            logger.error(f"BigQuery 메타데이터 로드 실패: {str(e)}")
            return False

    def get_cag_string(self) -> str:
        """
        Gemini 프롬프트 주입용 CAG 문자열 생성

        Returns:
            JSON 포맷의 CAG 메타데이터 문자열
        """
        if not self.cag_data:
            return "메타데이터가 로드되지 않았습니다."

        # 51개 판례를 JSON 배열로 포맷
        cag_json = json.dumps(
            {
                "precedent_count": len(self.cag_data),
                "cases": self.cag_data,
                "note": "이 메타데이터는 Context Cache를 통해 모든 사용자가 공유합니다."
            },
            ensure_ascii=False,
            indent=2
        )

        return cag_json

    def get_cag_summary(self) -> str:
        """
        프롬프트 토큰 절감용 간단한 CAG 요약

        Returns:
            간결한 판례 메타데이터 요약
        """
        if not self.cag_data:
            return "메타데이터가 로드되지 않았습니다."

        # 요약 모드: 각 판례의 핵심 정보만
        summary_lines = [
            f"# 51개 판례 메타데이터 (Context Cache)\n",
        ]

        for i, case in enumerate(self.cag_data, 1):
            summary_lines.append(
                f"{i}. Case #{case['case_id']}: "
                f"위자료={case['alimony_amount']:,}원, "
                f"유책사유={case['fault_type']}, "
                f"혼인기간={case['marriage_duration_years']}년"
            )

        return "\n".join(summary_lines)

    @staticmethod
    def create_and_load() -> Optional[str]:
        """
        CAG 로더를 생성하고 메타데이터를 로드한 후 CAG 문자열 반환 (편의 메서드)

        Returns:
            CAG 메타데이터 문자열 또는 None
        """
        loader = PrecedentCAGLoader()
        if loader.load_metadata():
            return loader.get_cag_string()
        return None


def load_precedent_cag() -> Optional[str]:
    """
    판례 CAG 로드 함수

    서버 시작시 이 함수를 호출하여 CAG를 로드합니다.

    Returns:
        CAG 메타데이터 문자열 또는 None
    """
    return PrecedentCAGLoader.create_and_load()
