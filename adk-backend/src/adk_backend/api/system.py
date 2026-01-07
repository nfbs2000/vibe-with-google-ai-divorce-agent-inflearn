#!/usr/bin/env python3
"""
시스템 상태 및 헬스체크 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import os
import psutil
from datetime import datetime
import asyncio

from ..utils.bigquery_helper import BigQueryHelper
from ..nlp.ai_client import get_ai_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])

# Pydantic 모델들
class HealthStatus(BaseModel):
    status: str  # 'healthy', 'degraded', 'unhealthy'
    timestamp: datetime
    version: str
    uptime: float
    checks: Dict[str, Any]

class SystemInfo(BaseModel):
    python_version: str
    platform: str
    cpu_count: int
    memory_total: int
    memory_available: int
    disk_usage: Dict[str, Any]
    environment: str

class ServiceStatus(BaseModel):
    name: str
    status: str  # 'online', 'offline', 'error'
    response_time: Optional[float] = None
    last_check: datetime
    error_message: Optional[str] = None

# 시스템 시작 시간
START_TIME = datetime.now()

# 의존성 주입
def get_bigquery_helper() -> BigQueryHelper:
    """BigQuery 헬퍼 인스턴스 반환"""
    return BigQueryHelper()

@router.get("/health", response_model=HealthStatus)
async def health_check(
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """
    시스템 헬스체크를 수행합니다.
    
    Returns:
        HealthStatus: 시스템 상태 정보
    """
    try:
        checks = {}
        overall_status = "healthy"
        
        # 1. BigQuery 연결 체크
        try:
            start_time = datetime.now()
            tables = bq_helper.list_tables()
            bq_response_time = (datetime.now() - start_time).total_seconds()
            
            checks["bigquery"] = {
                "status": "healthy",
                "response_time": bq_response_time,
                "table_count": len(tables)
            }
        except Exception as e:
            checks["bigquery"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_status = "degraded"
        # 2. AI 모델 상태 체크
        try:
            ai_client = get_ai_client()
            provider_status = ai_client.get_provider_status()
            current_provider = provider_status.get("current_provider", "none")
            providers = provider_status.get("providers", {})
            provider_info = {}
            if isinstance(providers, dict):
                provider_info = providers.get(current_provider) or {}
            current_model = provider_info.get("model")

            ai_status = "healthy" if current_provider != "none" else "degraded"
            if ai_status != "healthy" and overall_status == "healthy":
                overall_status = "degraded"

            checks["ai"] = {
                "status": ai_status,
                "provider": current_provider,
                "model": current_model,
            }
        except Exception as exc:
            checks["ai"] = {
                "status": "error",
                "error": str(exc)
            }
            if overall_status == "healthy":
                overall_status = "degraded"

        # 3. SQL 생성 엔진 정보
        checks["sql_engine"] = {
            "status": "informational",
            "mode": "dynamic-fusion",
            "description": "Gemini + 패턴 기반 템플릿으로 SQL을 조합합니다.",
            "components": [
                "Gemini LLM",
                "Pattern intent/entity extractor",
                "Template fallback library"
            ]
        }
        
        # 4. 메모리 사용량 체크
        try:
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent
            
            if memory_usage_percent > 90:
                memory_status = "unhealthy"
                overall_status = "degraded"
            elif memory_usage_percent > 75:
                memory_status = "degraded"
                if overall_status == "healthy":
                    overall_status = "degraded"
            else:
                memory_status = "healthy"
            
            checks["memory"] = {
                "status": memory_status,
                "usage_percent": memory_usage_percent,
                "available_gb": round(memory.available / (1024**3), 2)
            }
        except Exception as e:
            checks["memory"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 5. 디스크 사용량 체크
        try:
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            
            if disk_usage_percent > 90:
                disk_status = "unhealthy"
                overall_status = "degraded"
            elif disk_usage_percent > 80:
                disk_status = "degraded"
                if overall_status == "healthy":
                    overall_status = "degraded"
            else:
                disk_status = "healthy"
            
            checks["disk"] = {
                "status": disk_status,
                "usage_percent": round(disk_usage_percent, 2),
                "free_gb": round(disk.free / (1024**3), 2)
            }
        except Exception as e:
            checks["disk"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 6. 환경 변수 체크
        required_env_vars = [
            'GOOGLE_CLOUD_PROJECT',
            'BIGQUERY_DATASET'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            checks["environment"] = {
                "status": "degraded",
                "missing_variables": missing_vars
            }
            overall_status = "degraded"
        else:
            checks["environment"] = {
                "status": "healthy",
                "all_variables_present": True
            }
        
        # 업타임 계산
        uptime = (datetime.now() - START_TIME).total_seconds()
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.now(),
            version="1.0.0",
            uptime=uptime,
            checks=checks
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthStatus(
            status="unhealthy",
            timestamp=datetime.now(),
            version="1.0.0",
            uptime=(datetime.now() - START_TIME).total_seconds(),
            checks={"error": str(e)}
        )

@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    """
    시스템 정보를 반환합니다.
    
    Returns:
        SystemInfo: 시스템 정보
    """
    try:
        import platform
        import sys
        
        # 메모리 정보
        memory = psutil.virtual_memory()
        
        # 디스크 정보
        disk = psutil.disk_usage('/')
        disk_info = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "usage_percent": round((disk.used / disk.total) * 100, 2)
        }
        
        return SystemInfo(
            python_version=sys.version,
            platform=platform.platform(),
            cpu_count=psutil.cpu_count(),
            memory_total=memory.total,
            memory_available=memory.available,
            disk_usage=disk_info,
            environment=os.getenv('ENVIRONMENT', 'development')
        )
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"시스템 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/services", response_model=Dict[str, ServiceStatus])
async def get_service_status(
    bq_helper: BigQueryHelper = Depends(get_bigquery_helper)
):
    """
    외부 서비스 상태를 확인합니다.
    
    Returns:
        Dict[str, ServiceStatus]: 서비스별 상태 정보
    """
    services = {}
    
    # BigQuery 서비스 상태 확인
    try:
        start_time = datetime.now()
        tables = bq_helper.list_tables()
        response_time = (datetime.now() - start_time).total_seconds()
        
        services["bigquery"] = ServiceStatus(
            name="BigQuery",
            status="online",
            response_time=response_time,
            last_check=datetime.now()
        )
    except Exception as e:
        services["bigquery"] = ServiceStatus(
            name="BigQuery",
            status="error",
            last_check=datetime.now(),
            error_message=str(e)
        )

    return services

@router.get("/metrics")
async def get_system_metrics():
    """
    시스템 메트릭을 반환합니다.
    
    Returns:
        시스템 메트릭 정보
    """
    try:
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 정보
        memory = psutil.virtual_memory()
        
        # 디스크 I/O
        disk_io = psutil.disk_io_counters()
        
        # 네트워크 I/O
        net_io = psutil.net_io_counters()
        
        # 프로세스 정보
        process = psutil.Process()
        process_info = {
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_info": process.memory_info()._asdict(),
            "num_threads": process.num_threads(),
            "create_time": process.create_time()
        }
        
        return {
            "timestamp": datetime.now(),
            "uptime": (datetime.now() - START_TIME).total_seconds(),
            "cpu": {
                "usage_percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            },
            "disk_io": {
                "read_count": disk_io.read_count if disk_io else 0,
                "write_count": disk_io.write_count if disk_io else 0,
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0
            },
            "network_io": {
                "bytes_sent": net_io.bytes_sent if net_io else 0,
                "bytes_recv": net_io.bytes_recv if net_io else 0,
                "packets_sent": net_io.packets_sent if net_io else 0,
                "packets_recv": net_io.packets_recv if net_io else 0
            },
            "process": process_info
        }
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"시스템 메트릭 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/restart")
async def restart_service():
    """
    서비스 재시작 (개발 환경에서만 사용)
    
    Returns:
        재시작 상태
    """
    if os.getenv('ENVIRONMENT', 'development') != 'development':
        raise HTTPException(
            status_code=403,
            detail="재시작은 개발 환경에서만 가능합니다."
        )
    
    logger.info("Service restart requested")
    
    # TODO: 실제 재시작 로직 구현
    return {
        "status": "success",
        "message": "서비스 재시작이 요청되었습니다.",
        "timestamp": datetime.now()
    }
