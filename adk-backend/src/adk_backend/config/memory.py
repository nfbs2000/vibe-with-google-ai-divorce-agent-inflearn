"""
Memory Service 설정

개발: InMemoryMemoryService (휘발성, 무료)
프로덕션: VertexAiMemoryBankService (영구, Vertex AI)
"""
import os
from google.adk.memory import (
    InMemoryMemoryService,
    VertexAiMemoryBankService
)

# 개발용 메모리 서비스 (재시작 시 소실)
dev_memory_service = InMemoryMemoryService()

# 프로덕션용 메모리 서비스 (Vertex AI Memory Bank)
production_memory_service = VertexAiMemoryBankService(
    project=os.getenv("GOOGLE_CLOUD_PROJECT", "pio-test-36cf5"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "asia-northeast3")
)


def get_memory_service():
    """
    환경 변수에 따라 적절한 메모리 서비스 반환

    환경변수:
        MEMORY_SERVICE: 'inmemory' | 'memorybank'
        ENVIRONMENT: 'development' | 'staging' | 'production'

    우선순위:
        1. MEMORY_SERVICE 명시적 지정
        2. ENVIRONMENT 기반 자동 선택

    Returns:
        InMemoryMemoryService 또는 VertexAiMemoryBankService
    """
    # 명시적 지정 (최우선)
    memory_service_type = os.getenv("MEMORY_SERVICE")

    if memory_service_type == "inmemory":
        print("🧪 Using InMemory Service (명시적 지정)")
        return dev_memory_service

    if memory_service_type == "memorybank":
        print("🏢 Using Memory Bank (명시적 지정)")
        return production_memory_service

    # 환경 기반 자동 선택
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        print("🏢 Using Memory Bank (프로덕션 환경)")
        return production_memory_service
    elif env == "staging":
        print("🏢 Using Memory Bank (스테이징 환경)")
        return production_memory_service
    else:
        print("🧪 Using InMemory Service (개발 환경)")
        return dev_memory_service


# 전역 메모리 서비스 인스턴스
memory_service = get_memory_service()
