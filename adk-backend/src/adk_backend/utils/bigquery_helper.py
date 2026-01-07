import os
import logging
import asyncio
from functools import partial
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import json

try:
    from google.cloud import bigquery
    from google.cloud.exceptions import NotFound, BadRequest
    from google.api_core.exceptions import Forbidden
    from google.oauth2 import service_account
except ImportError:
    bigquery = None
    NotFound = Exception
    BadRequest = Exception
    Forbidden = Exception
    service_account = None

logger = logging.getLogger(__name__)

class BigQueryHelper:
    """BigQuery 연동을 위한 헬퍼 클래스"""
    
    def __init__(self, project_id: str = None, dataset_name: str = None, credentials_path: str = None):
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.dataset_name = dataset_name or os.getenv('BIGQUERY_DATASET', 'analytics_sfg')
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self._permission_error = False
        self._last_error: Optional[str] = None
        
        if not bigquery:
            logger.warning("Google Cloud BigQuery library not installed. Install with: pip install google-cloud-bigquery")
            self.client = None
            return
        
        try:
            # 인증 설정
            if self.credentials_path and os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(self.credentials_path)
                self.client = bigquery.Client(project=self.project_id, credentials=credentials)
            else:
                # 기본 인증 사용 (환경 변수 또는 gcloud auth)
                self.client = bigquery.Client(project=self.project_id)
            
            logger.info(f"BigQuery client initialized for project: {self.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            self.client = None
            self._last_error = str(e)
    
    def is_connected(self) -> bool:
        """BigQuery 연결 상태 확인"""
        if not self.client:
            return False
        
        try:
            # 간단한 쿼리로 연결 테스트
            query = "SELECT 1 as test"
            job = self.client.query(query)
            list(job.result())  # 결과 소비
            return True
        except Forbidden as e:
            logger.error(f"BigQuery permission denied during connection test: {e}")
            self._permission_error = True
            self._last_error = str(e)
            return False
        except Exception as e:
            logger.error(f"BigQuery connection test failed: {e}")
            self._last_error = str(e)
            return False
    
    def execute_query(self, sql: str, timeout: int = 30) -> List[Dict[str, Any]]:
        """SQL 쿼리를 실행하고 결과를 반환합니다."""
        if not self.client:
            raise RuntimeError("BigQuery client not initialized")
        
        try:
            logger.info(f"Executing query: {sql[:100]}...")
            
            # 쿼리 실행
            job_config = bigquery.QueryJobConfig()
            job_config.use_query_cache = True
            job_config.use_legacy_sql = False
            
            query_job = self.client.query(sql, job_config=job_config)
            
            # 결과 대기
            results = query_job.result(timeout=timeout)
            
            # 결과를 딕셔너리 리스트로 변환
            rows = []
            for row in results:
                row_dict = {}
                for key, value in row.items():
                    # BigQuery 타입을 Python 타입으로 변환
                    if isinstance(value, datetime):
                        row_dict[key] = value.isoformat()
                    elif isinstance(value, date):
                        row_dict[key] = value.isoformat()
                    elif hasattr(value, 'total_seconds'):  # timedelta
                        row_dict[key] = value.total_seconds()
                    else:
                        row_dict[key] = value
                rows.append(row_dict)
            
            logger.info(f"Query executed successfully. Returned {len(rows)} rows.")
            return rows
            
        except BadRequest as e:
            error_msg = f"SQL syntax error: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Forbidden as e:
            self._permission_error = True
            self._last_error = str(e)
            error_msg = f"BigQuery permission denied: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Query execution failed: {str(e)}"
            logger.error(error_msg)
            self._last_error = str(e)
            raise RuntimeError(error_msg) from e

    async def execute_query_async(self, sql: str, timeout: int = 30) -> List[Dict[str, Any]]:
        """비동기적으로 SQL 쿼리를 실행합니다."""
        loop = asyncio.get_running_loop()
        func = partial(self.execute_query, sql, timeout)
        return await loop.run_in_executor(None, func)
    
    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """테이블 스키마 정보 조회"""
        if not self.client:
            return None
        
        try:
            table_ref = self.client.dataset(self.dataset_name).table(table_name)
            table = self.client.get_table(table_ref)
            
            schema_info = {
                "table_name": table_name,
                "description": table.description or "",
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None,
                "columns": []
            }
            
            for field in table.schema:
                column_info = {
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description or ""
                }
                schema_info["columns"].append(column_info)
            
            return schema_info
        except Forbidden as e:
            logger.error(f"Permission denied when fetching schema for {table_name}: {e}")
            self._permission_error = True
            self._last_error = str(e)
            return None
        except NotFound:
            logger.warning(f"Table {table_name} not found in dataset {self.dataset_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {e}")
            self._last_error = str(e)
            return None
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """데이터셋의 모든 테이블 목록 조회"""
        if not self.client:
            return []
        
        try:
            dataset_ref = self.client.dataset(self.dataset_name)
            tables = list(self.client.list_tables(dataset_ref))
            
            table_list = []
            for table in tables:
                table_info = {
                    "name": table.table_id,
                    "type": table.table_type,
                    "created": table.created.isoformat() if table.created else None,
                    "num_rows": getattr(table, 'num_rows', 0),
                    "size_bytes": getattr(table, 'num_bytes', 0)
                }
                table_list.append(table_info)
            
            return table_list
        except Forbidden as e:
            logger.error(f"Permission denied when listing tables in dataset {self.dataset_name}: {e}")
            self._permission_error = True
            self._last_error = str(e)
            return []
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            self._last_error = str(e)
            return []

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """특정 테이블의 기본 정보를 반환"""
        if not self.client:
            return None
        try:
            table_ref = self.client.dataset(self.dataset_name).table(table_name)
            table = self.client.get_table(table_ref)
            return {
                "table_id": table.table_id,
                "full_table_id": getattr(table, "full_table_id", None),
                "num_rows": getattr(table, "num_rows", 0),
                "num_bytes": getattr(table, "num_bytes", 0),
                "created": table.created.isoformat() if getattr(table, "created", None) else None,
                "modified": table.modified.isoformat() if getattr(table, "modified", None) else None,
                "description": table.description or ""
            }
        except Forbidden as e:
            logger.error(f"Permission denied when accessing table {table_name}: {e}")
            self._permission_error = True
            self._last_error = str(e)
            return None
        except NotFound:
            logger.warning(f"Table {table_name} not found in dataset {self.dataset_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            self._last_error = str(e)
            return None
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """테이블의 샘플 데이터 조회"""
        sql = f"SELECT * FROM `{self.project_id}.{self.dataset_name}.{table_name}` LIMIT {limit}"
        try:
            rows = self.execute_query(sql)
            return rows, None
        except Exception as e:
            return [], str(e)
    
    def get_table_stats(self, table_name: str) -> Optional[Dict[str, Any]]:
        """테이블 통계 정보 조회"""
        if not self.client:
            return None
        
        try:
            # 기본 통계
            stats_sql = f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT DATE(created_at)) as date_range_days
            FROM `{self.project_id}.{self.dataset_name}.{table_name}`
            """
            
            results = self.execute_query(stats_sql)
            if not results:
                return None
            
            stats = dict(results[0])
            
            # 테이블 메타데이터
            schema_info = self.get_table_schema(table_name)
            if schema_info:
                stats.update({
                    "size_bytes": schema_info["num_bytes"],
                    "columns_count": len(schema_info["columns"]),
                    "created": schema_info["created"],
                    "modified": schema_info["modified"]
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats for table {table_name}: {e}")
            self._last_error = str(e)
            return None
    
    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """SQL 쿼리 유효성 검사 (dry run)"""
        if not self.client:
            return False, "BigQuery client not initialized"
        
        try:
            job_config = bigquery.QueryJobConfig()
            job_config.dry_run = True
            job_config.use_query_cache = False
            
            query_job = self.client.query(sql, job_config=job_config)
            
            # dry run이므로 실제 실행되지 않음
            logger.info(f"SQL validation successful. Estimated bytes: {query_job.total_bytes_processed}")
            return True, None
            
        except BadRequest as e:
            error_msg = f"SQL validation failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Forbidden as e:
            self._permission_error = True
            self._last_error = str(e)
            error_msg = f"BigQuery permission denied during validation: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"SQL validation error: {str(e)}"
            logger.error(error_msg)
            self._last_error = str(e)
            return False, error_msg
    
    def get_dataset_info(self) -> Optional[Dict[str, Any]]:
        """데이터셋 정보 조회"""
        if not self.client:
            return None
        
        try:
            dataset_ref = self.client.dataset(self.dataset_name)
            dataset = self.client.get_dataset(dataset_ref)
            
            return {
                "dataset_id": dataset.dataset_id,
                "project": dataset.project,
                "description": dataset.description or "",
                "created": dataset.created.isoformat() if dataset.created else None,
                "modified": dataset.modified.isoformat() if dataset.modified else None,
                "location": dataset.location,
                "labels": dict(dataset.labels) if dataset.labels else {}
            }
            
        except Forbidden as e:
            logger.error(f"Permission denied when retrieving dataset info for {self.dataset_name}: {e}")
            self._permission_error = True
            self._last_error = str(e)
            return None
        except Exception as e:
            logger.error(f"Failed to get dataset info: {e}")
            self._last_error = str(e)
            return None
    
    def create_table_if_not_exists(self, table_name: str, schema: List[bigquery.SchemaField]) -> bool:
        """테이블이 존재하지 않으면 생성"""
        if not self.client:
            return False
        
        try:
            table_ref = self.client.dataset(self.dataset_name).table(table_name)
            
            # 테이블 존재 여부 확인
            try:
                self.client.get_table(table_ref)
                logger.info(f"Table {table_name} already exists")
                return True
            except NotFound:
                pass
            
            # 테이블 생성
            table = bigquery.Table(table_ref, schema=schema)
            table = self.client.create_table(table)
            
            logger.info(f"Created table {table_name}")
            return True
        except Forbidden as e:
            logger.error(f"Permission denied when creating table {table_name}: {e}")
            self._permission_error = True
            self._last_error = str(e)
            return False
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            self._last_error = str(e)
            return False
    
    def insert_rows(self, table_name: str, rows: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """테이블에 데이터 삽입"""
        if not self.client:
            return False, "BigQuery client not initialized"
        
        try:
            table_ref = self.client.dataset(self.dataset_name).table(table_name)
            table = self.client.get_table(table_ref)
            
            errors = self.client.insert_rows_json(table, rows)
            
            if errors:
                error_msg = f"Insert errors: {errors}"
                logger.error(error_msg)
                return False, error_msg
            
            logger.info(f"Successfully inserted {len(rows)} rows into {table_name}")
            return True, None
        except Forbidden as e:
            error_msg = f"Permission denied when inserting rows into {table_name}: {e}"
            logger.error(error_msg)
            self._permission_error = True
            self._last_error = str(e)
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to insert rows: {str(e)}"
            logger.error(error_msg)
            self._last_error = str(e)
            return False, error_msg
    
    def get_query_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 쿼리 히스토리 조회 (간단한 구현)"""
        # 실제 구현에서는 별도의 로그 테이블이나 캐시를 사용
        # 현재는 빈 리스트 반환
        return []
    
    def estimate_query_cost(self, sql: str) -> Optional[Dict[str, Any]]:
        """쿼리 비용 추정"""
        if not self.client:
            return None
        
        try:
            job_config = bigquery.QueryJobConfig()
            job_config.dry_run = True
            job_config.use_query_cache = False
            
            query_job = self.client.query(sql, job_config=job_config)
            
            # BigQuery 가격 계산 (2023년 기준: $5 per TB)
            bytes_processed = query_job.total_bytes_processed or 0
            tb_processed = bytes_processed / (1024 ** 4)  # bytes to TB
            estimated_cost_usd = tb_processed * 5.0
            
            return {
                "bytes_processed": bytes_processed,
                "tb_processed": round(tb_processed, 6),
                "estimated_cost_usd": round(estimated_cost_usd, 4),
                "cache_hit": query_job.cache_hit if hasattr(query_job, 'cache_hit') else False
            }
        except Forbidden as e:
            logger.error(f"Permission denied when estimating query cost: {e}")
            self._permission_error = True
            self._last_error = str(e)
            return None
        except Exception as e:
            logger.error(f"Failed to estimate query cost: {e}")
            self._last_error = str(e)
            return None

    @property
    def permission_error(self) -> bool:
        return self._permission_error

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

# 전역 BigQuery 헬퍼 인스턴스
_bigquery_helper = None

def get_bigquery_helper() -> BigQueryHelper:
    """BigQuery 헬퍼 싱글톤 인스턴스 반환"""
    global _bigquery_helper
    if _bigquery_helper is None:
        _bigquery_helper = BigQueryHelper()
    return _bigquery_helper
