"""
BigQuery MCP Compatible Tools
강좌 Chapter 5에서 다루는 BigQuery Tool 구현체입니다.

데이터 소스:
- `data/court_cases/metadata_json/*.json` (예: `data/court_cases/metadata_json/238783.json`)
- `scripts/index_precedents_v2.py`가 BigQuery `precedent_cases`에 적재

벡터 임베딩:
- `full_text_embedding`은 `key_summary`, `alimony_reason`, `fault_type`를 묶어 생성됩니다.

BigQuery Table (precedent_cases) 주요 컬럼:
- case_id: STRING
- case_number: STRING (metadata_json의 filename 기반)
- fault_type: STRING
- alimony_amount: INT64
- property_ratio_plaintiff: FLOAT64
- marriage_duration_years: INT64
- summary: STRING (metadata_json의 key_summary)
- full_text_embedding: FLOAT64 (REPEATED)
- gemini_file_id: STRING
"""
import logging
from typing import Dict, Any, List, Optional
from google.cloud import bigquery
from google.cloud.bigquery.job import QueryJobConfig
from ..nlp.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

class BigQueryTools:
    def __init__(self, project_id: str = None, dataset_id: str = "divorce_analytics"):
        # project_id가 None이면 환경변수나 credentials에서 자동 로드
        self.client = bigquery.Client(project=project_id)
        self.dataset_id = dataset_id
        
    def list_templates(self) -> Dict[str, Any]:
        """
        사용 가능한 SQL 템플릿 목록을 반환합니다.
        AI 에이전트가 어떤 분석을 할 수 있는지 스스로 파악하는 데 사용됩니다.
        """
        templates = {
            "precedents_by_fault": {
                "description": "유책 사유별 판례 통계 조회 (평균 위자료, 건수)",
                "parameters": ["fault_type"],
                "sql": """
                    SELECT
                        fault_type,
                        COUNT(*) as case_count,
                        AVG(CAST(alimony_amount AS FLOAT64)) as avg_alimony,
                        AVG(property_ratio_plaintiff) as avg_property_ratio,
                        MIN(judgment_date) as earliest_case,
                        MAX(judgment_date) as latest_case
                    FROM `{project}.{dataset}.precedent_cases`
                    WHERE fault_type = @fault_type
                    GROUP BY fault_type
                    ORDER BY case_count DESC
                """
            },
            "case_search": {
                "description": "사건번호 또는 판례 ID로 판례 검색",
                "parameters": ["case_id"],
                "sql": """
                    SELECT
                        case_id,
                        case_number,
                        court_name,
                        judgment_date,
                        fault_type,
                        alimony_amount,
                        property_ratio_plaintiff,
                        marriage_duration_years,
                        summary,
                        tags
                    FROM `{project}.{dataset}.precedent_cases`
                    WHERE case_id = @case_id
                    LIMIT 1
                """
            },
            "court_statistics": {
                "description": "법원별 판례 통계",
                "parameters": [],
                "sql": """
                    SELECT
                        court_name,
                        COUNT(*) as case_count,
                        AVG(CAST(alimony_amount AS FLOAT64)) as avg_alimony,
                        AVG(property_ratio_plaintiff) as avg_property_ratio,
                        STRING_AGG(DISTINCT fault_type, ', ') as fault_types
                    FROM `{project}.{dataset}.precedent_cases`
                    WHERE court_name IS NOT NULL
                    GROUP BY court_name
                    ORDER BY case_count DESC
                """
            },
            "property_division_analysis": {
                "description": "재산분할 비율 분석 (청구인 기준)",
                "parameters": [],
                "sql": """
                    SELECT
                        ROUND(property_ratio_plaintiff * 100, 1) as property_percentage,
                        COUNT(*) as case_count,
                        AVG(CAST(alimony_amount AS FLOAT64)) as avg_alimony,
                        MIN(property_ratio_plaintiff) as min_ratio,
                        MAX(property_ratio_plaintiff) as max_ratio
                    FROM `{project}.{dataset}.precedent_cases`
                    WHERE property_ratio_plaintiff > 0
                    GROUP BY ROUND(property_ratio_plaintiff * 100, 1)
                    ORDER BY property_percentage ASC
                """
            },
            "marriage_duration_stats": {
                "description": "결혼 기간별 판례 통계",
                "parameters": [],
                "sql": """
                    SELECT
                        CASE
                            WHEN marriage_duration_years <= 5 THEN '5년 이하'
                            WHEN marriage_duration_years <= 10 THEN '5-10년'
                            WHEN marriage_duration_years <= 20 THEN '10-20년'
                            ELSE '20년 이상'
                        END as duration_group,
                        COUNT(*) as case_count,
                        AVG(CAST(alimony_amount AS FLOAT64)) as avg_alimony,
                        AVG(property_ratio_plaintiff) as avg_property_ratio
                    FROM `{project}.{dataset}.precedent_cases`
                    WHERE marriage_duration_years > 0
                    GROUP BY duration_group
                    ORDER BY CASE
                        WHEN duration_group = '5년 이하' THEN 1
                        WHEN duration_group = '5-10년' THEN 2
                        WHEN duration_group = '10-20년' THEN 3
                        ELSE 4
                    END
                """
            },
            "recent_cases": {
                "description": "최근 N건의 판례 조회",
                "parameters": ["limit"],
                "sql": """
                    SELECT
                        case_id,
                        case_number,
                        court_name,
                        judgment_date,
                        fault_type,
                        alimony_amount,
                        property_ratio_plaintiff,
                        summary
                    FROM `{project}.{dataset}.precedent_cases`
                    WHERE judgment_date IS NOT NULL
                    ORDER BY judgment_date DESC
                    LIMIT @limit
                """
            },
            "similar_cases_by_vector": {
                "description": "벡터 검색으로 유사 판례 찾기 (full_text_embedding 사용)",
                "parameters": ["embedding_vector", "limit"],
                "sql": """
                    SELECT
                        base.case_id,
                        base.case_number,
                        base.court_name,
                        base.fault_type,
                        base.summary,
                        base.alimony_amount,
                        base.judgment_date,
                        distance
                    FROM VECTOR_SEARCH(
                        TABLE `{project}.{dataset}.precedent_cases`,
                        'full_text_embedding',
                        (SELECT @embedding_vector AS query_vector),
                        top_k => @limit
                    )
                """
            },
            "semantic_search": {
                "description": "사람의 언어로 유사 판례 검색 (벡터 변환 자동 수행)",
                "parameters": ["query_text", "limit"],
                "sql": "-- This is handled by search_similar_cases method programmatically"
            }
        }
        return {"templates": templates}

    def search_similar_cases(self, query_text: str, limit: int = 5) -> Dict[str, Any]:
        """
        자연어 쿼리를 벡터로 변환하여 유사 판례를 검색합니다.
        full_text_embedding은 key_summary/alimony_reason/fault_type 기반으로 생성됩니다.
        """
        try:
            # 1. Generate Embedding
            gemini = get_gemini_client()
            embedding = gemini.get_embedding(query_text)
            
            if not embedding:
                return {"success": False, "error": "Failed to generate embedding for query"}
                
            # 2. Execute Vector Search Query
            # We use the 'similar_cases_by_vector' logic but inject the vector directly
            
            # Using the template definition for consistency
            templates = self.list_templates()["templates"]
            raw_sql = templates["similar_cases_by_vector"]["sql"]
            
            # Replace project/dataset placeholders
            final_sql = raw_sql.replace("{project}", self.client.project).replace("{dataset}", self.dataset_id)
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("embedding_vector", "FLOAT64", embedding),
                    bigquery.ScalarQueryParameter("limit", "INT64", limit)
                ]
            )
            
            logger.info(f"Executing Semantic Search for: '{query_text}'")
            query_job = self.client.query(final_sql, job_config=job_config)
            results = list(query_job.result())
            
            rows = []
            for row in results:
                row_dict = {}
                for key, value in row.items():
                    row_dict[key] = str(value) if value is not None else None
                rows.append(row_dict)
                
            return {
                "success": True,
                "rows": rows,
                "total_rows": len(rows),
                "query_text": query_text
            }
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return {"success": False, "error": str(e)}

    def dry_run(self, sql: str) -> Dict[str, Any]:
        """
        SQL 문법을 검증하고 예상 비용을 계산합니다. (실행하지 않음)
        """
        job_config = QueryJobConfig(dry_run=True, use_query_cache=False)
        try:
            logger.info(f"Dry run SQL: {sql[:100]}...")
            query_job = self.client.query(sql, job_config=job_config)
            
            return {
                "valid": True,
                "estimated_bytes": query_job.total_bytes_processed,
                "schema": [field.name for field in query_job.schema] if query_job.schema else []
            }
        except Exception as e:
            logger.warning(f"Dry run failed: {e}")
            return {
                "valid": False, 
                "error": str(e),
                "suggestion": "Check table names and column names. Remember TIMESTAMP_SUB expects DAY, not MONTH."
            }

    def execute(self, sql: str) -> Dict[str, Any]:
        """
        SQL 쿼리를 실제로 실행하고 결과를 반환합니다.
        """
        try:
            logger.info(f"Executing SQL: {sql[:100]}...")
            query_job = self.client.query(sql)
            results = list(query_job.result())
            
            # Serialize results
            rows = []
            for row in results:
                # Convert Row to dict
                row_dict = {}
                for key, value in row.items():
                    # Handle date/timestamp serialization if needed
                    row_dict[key] = str(value) if value is not None else None
                rows.append(row_dict)
                
            return {
                "success": True,
                "rows": rows,
                "total_rows": len(rows),
                "job_id": query_job.job_id
            }
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {"success": False, "error": str(e)}

# 인스턴스 생성을 위한 헬퍼 함수들 (ADK에서 사용)
_bq_tool_instance = None

def get_bq_tool():
    global _bq_tool_instance
    if _bq_tool_instance is None:
        _bq_tool_instance = BigQueryTools()
    return _bq_tool_instance

def bigquery_list_templates():
    """List available SQL templates for divorce analytics."""
    return get_bq_tool().list_templates()

def bigquery_dry_run(sql: str):
    """Validate SQL query syntax and estimate cost without execution."""
    return get_bq_tool().dry_run(sql)

def bigquery_execute(sql: str):
    """Execute SQL query and return results."""
    return get_bq_tool().execute(sql)

def bigquery_search_similar_cases(query_text: str, limit: int = 5):
    """Search for similar cases using vector embeddings from natural language query."""
    return get_bq_tool().search_similar_cases(query_text, limit)


def bigquery_render_template(template_name: str, params: Dict[str, Any]) -> str:
    """
    Render SQL template by filling in project/dataset names.
    Real parameters are handled via BigQuery query parameters (@param).
    """
    tool = get_bq_tool()
    templates = tool.list_templates()["templates"]
    
    if template_name not in templates:
        raise ValueError(f"Unknown template: {template_name}")
        
    template_def = templates[template_name]
    raw_sql = template_def["sql"]
    
    # Replace project/dataset placeholders
    project_id = tool.client.project
    dataset_id = tool.dataset_id
    
    rendered_sql = raw_sql.replace("{project}", project_id).replace("{dataset}", dataset_id)
    return rendered_sql
