#!/usr/bin/env python3
"""
데이터 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..utils.bigquery_helper import BigQueryHelper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])

# Pydantic 모델들
class TableInfo(BaseModel):
    table_name: str
    description: str
    row_count: Optional[int] = None
    last_modified: Optional[datetime] = None
    table_schema: Optional[List[Dict[str, Any]]] = Field(default=None, alias="schema")

class DataSource(BaseModel):
    name: str
    display_name: str
    description: str
    table_count: int
    total_rows: Optional[int] = None
    last_updated: Optional[datetime] = None
    status: str  # 'active', 'inactive', 'error'
    error: Optional[str] = None

class QueryExecutionRequest(BaseModel):
    sql_query: str
    dry_run: Optional[bool] = False
    max_results: Optional[int] = 1000

class QueryExecutionResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None
    query_info: Optional[Dict[str, Any]] = None

# 의존성 주입
def get_bigquery_helper() -> BigQueryHelper:
    """BigQuery 헬퍼 인스턴스 반환"""
    return BigQueryHelper()

@router.get("/sources", response_model=List[DataSource])
async def get_data_sources(
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """
    사용 가능한 데이터 소스 목록을 반환합니다.
    
    Returns:
        List[DataSource]: 데이터 소스 목록
    """
    try:
        logger.info("Retrieving data sources")
        
        table_map = {table["name"]: table for table in bq_helper.list_tables()}

        # 이혼 도메인 관련 주요 테이블 정의
        definitions = [
            {
                "name": "precedent_cases",
                "display_name": "🏛️ 전국 이혼 판례 데이터",
                "description": "과거 이혼 판결 통계, 위자료/재산분할 액수, 양육권 판결 결과",
                "tables": ["precedent_cases"]
            },
            {
                "name": "divorce_evidence_templates",
                "display_name": "� 이혼 증거 서식 및 가이드",
                "description": "소장 작성 예시, 합법적 증거 수집 가이드 및 서식 데이터",
                "tables": ["divorce_evidence_templates"]
            },
            {
                "name": "counseling_knowledge_base",
                "display_name": "📚 전문 상담 지식베이스",
                "description": "가사 소송 관련 FAQ, 법률 용어 사전, 절차 안내 정보",
                "tables": ["knowledge_base"]
            }
        ]

        data_sources: List[DataSource] = []

        for definition in definitions:
            total_rows = 0
            last_updated: Optional[datetime] = None
            available_tables = 0

            for table_name in definition["tables"]:
                table_info = bq_helper.get_table_info(table_name)
                if table_info:
                    available_tables += 1
                    total_rows += table_info.get("num_rows", 0)
                    timestamp_str = table_info.get("modified") or table_info.get("created")
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        except ValueError:
                            timestamp = None
                        if timestamp and (last_updated is None or timestamp > last_updated):
                            last_updated = timestamp

            permission_error = bq_helper.permission_error
            status = "active" if available_tables > 0 else ("error" if permission_error else "inactive")
            error_message = bq_helper.last_error if status == "error" else None

            data_sources.append(
                DataSource(
                    name=definition["name"],
                    display_name=definition["display_name"],
                    description=definition["description"],
                    table_count=len(definition["tables"]),
                    total_rows=total_rows,
                    last_updated=last_updated,
                    status=status,
                    error=error_message
                )
            )

        # 존재하는데 정의되지 않은 테이블도 노출
        defined_tables = {table for d in definitions for table in d["tables"]}
        for table_name, table_info in table_map.items():
            if table_name in defined_tables:
                continue
            metadata = bq_helper.get_table_info(table_name) or {}
            permission_error = bq_helper.permission_error
            error_message = bq_helper.last_error if permission_error else None
            timestamp_str = metadata.get("modified") or metadata.get("created")
            last_updated = None
            if timestamp_str:
                try:
                    last_updated = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    last_updated = None

            data_sources.append(
                DataSource(
                    name=table_name,
                    display_name=table_name,
                    description=f"{table_name} 테이블",
                    table_count=1,
                    total_rows=metadata.get("num_rows", 0),
                    last_updated=last_updated,
                    status="error" if permission_error else "active",
                    error=error_message
                )
            )

        if bq_helper.permission_error:
            logger.warning("One or more data sources are unavailable due to BigQuery permission issues.")

        return data_sources
        
    except Exception as e:
        logger.error(f"Error retrieving data sources: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"데이터 소스 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/tables", response_model=List[TableInfo])
async def get_tables(
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """
    사용 가능한 테이블 목록을 반환합니다.
    
    Returns:
        List[TableInfo]: 테이블 정보 목록
    """
    try:
        logger.info("Retrieving table list")
        
        tables = bq_helper.list_tables()
        table_infos = []
        
        for table in tables:
            table_name = table.get("name")
            if not table_name:
                continue
            try:
                table_info = bq_helper.get_table_info(table_name) or {}
                schema_info = bq_helper.get_table_schema(table_name) or {}
                
                table_infos.append(TableInfo(
                    table_name=table_name,
                    description=table_info.get("description") or f"{table_name} 테이블",
                    row_count=table_info.get('num_rows'),
                    last_modified=datetime.fromisoformat(table_info["modified"].replace("Z", "+00:00")) if table_info.get("modified") else None,
                    table_schema=schema_info.get("columns") if schema_info else None
                ))
                
            except Exception as e:
                logger.warning(f"Could not get info for table {table_name}: {e}")
                table_infos.append(TableInfo(
                    table_name=table_name,
                    description=f"{table_name} 테이블 (정보 조회 실패)"
                ))
        
        return table_infos
        
    except Exception as e:
        logger.error(f"Error retrieving tables: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"테이블 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/tables/{table_name}/schema")
async def get_table_schema(
    table_name: str,
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """
    특정 테이블의 스키마 정보를 반환합니다.
    
    Args:
        table_name: 테이블 이름
    
    Returns:
        테이블 스키마 정보
    """
    try:
        logger.info(f"Retrieving schema for table: {table_name}")
        
        schema = bq_helper.get_table_schema(table_name)
        
        if not schema or "columns" not in schema:
            raise HTTPException(
                status_code=404,
                detail=f"테이블 '{table_name}'을 찾을 수 없습니다."
            )
        
        return {
            "table_name": table_name,
            "schema": schema,
            "field_count": len(schema["columns"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving schema for {table_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"스키마 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/tables/{table_name}/sample")
async def get_table_sample(
    table_name: str,
    limit: int = Query(10, ge=1, le=100),
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """
    특정 테이블의 샘플 데이터를 반환합니다.
    
    Args:
        table_name: 테이블 이름
        limit: 조회할 행 수 (1-100)
    
    Returns:
        샘플 데이터
    """
    try:
        logger.info(f"Retrieving sample data for table: {table_name}")
        
        # 샘플 쿼리 생성
        sql_query = f"""
        SELECT *
        FROM `{bq_helper.project_id}.{bq_helper.dataset_name}.{table_name}`
        LIMIT {limit}
        """
        
        # 쿼리 실행
        results = bq_helper.execute_query(sql_query)
        
        return {
            "table_name": table_name,
            "sample_data": results,
            "row_count": len(results),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error retrieving sample data for {table_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"샘플 데이터 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/execute", response_model=QueryExecutionResponse)
async def execute_sql_query(
    request: QueryExecutionRequest,
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """
    SQL 쿼리를 실행합니다.
    
    Args:
        request: 쿼리 실행 요청
    
    Returns:
        QueryExecutionResponse: 쿼리 실행 결과
    """
    try:
        start_time = datetime.now()
        
        logger.info(f"Executing SQL query: {request.sql_query[:100]}...")
        
        # 쿼리 검증 (기본적인 보안 체크)
        if not request.sql_query.strip().upper().startswith('SELECT'):
            raise HTTPException(
                status_code=400,
                detail="SELECT 쿼리만 실행할 수 있습니다."
            )
        
        # 드라이 런 체크
        if request.dry_run:
            # TODO: 쿼리 유효성 검사만 수행
            return QueryExecutionResponse(
                success=True,
                data=None,
                row_count=0,
                execution_time=0.0,
                query_info={"dry_run": True, "query_valid": True}
            )
        
        # 쿼리 실행
        results = bq_helper.execute_query(request.sql_query)
        
        # 결과 제한
        if len(results) > request.max_results:
            results = results[:request.max_results]
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return QueryExecutionResponse(
            success=True,
            data=results,
            row_count=len(results),
            execution_time=execution_time,
            query_info={
                "max_results_applied": len(results) == request.max_results
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing SQL query: {e}")
        return QueryExecutionResponse(
            success=False,
            error=str(e),
            execution_time=(datetime.now() - start_time).total_seconds()
        )

@router.get("/stats")
async def get_data_stats(
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """
    데이터 통계 정보를 반환합니다.
    
    Returns:
        데이터 통계 정보
    """
    try:
        logger.info("Retrieving data statistics")
        
        tables = bq_helper.list_tables()
        stats = {
            "total_tables": len(tables),
            "total_rows": 0,
            "table_stats": []
        }
        
        for table in tables:
            table_name = table.get("name")
            if not table_name:
                continue
            try:
                table_info = bq_helper.get_table_info(table_name)
                row_count = table_info.get('num_rows', 0) if table_info else 0
                stats["total_rows"] += row_count
                
                stats["table_stats"].append({
                    "table_name": table_name,
                    "row_count": row_count,
                    "last_modified": table_info.get('modified') if table_info else None
                })
                
            except Exception as e:
                logger.warning(f"Could not get stats for table {table_name}: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving data stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"데이터 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )
