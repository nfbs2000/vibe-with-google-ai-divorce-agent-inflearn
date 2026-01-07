from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 런타임 설정."""

    model_config = SettingsConfigDict(
        # .env 파일은 app.py에서 load_dotenv()로 로드되므로
        # 여기서는 환경 변수에서만 읽음
        populate_by_name=True,
        extra="allow"  # 추가 필드 허용
    )

    # Google Cloud 설정
    google_project_id: str = Field(alias="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: Optional[Path] = Field(
        default=None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    bigquery_default_dataset: Optional[str] = Field(default=None, alias="BIGQUERY_DEFAULT_DATASET")
    bigquery_dataset: Optional[str] = Field(default=None, alias="BIGQUERY_DATASET")
    bigquery_location: str = Field(default="US", alias="BIGQUERY_LOCATION")

    # API Keys
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")

    # ADK Model Configuration (Gemini 3.0 Pro Preview, US region only)
    adk_model_name: str = Field(default="gemini-3-pro-preview", alias="ADK_MODEL_NAME")
    adk_model_region: str = Field(default="us-central1", alias="ADK_MODEL_REGION")
    adk_model_endpoint: str = Field(
        default="us-central1-aiplatform.googleapis.com", alias="ADK_MODEL_ENDPOINT"
    )

    # File Search Configuration
    file_search_store_name: Optional[str] = Field(default=None, alias="FILE_SEARCH_STORE_NAME")

    # CAG (Context-Augmented Generation) 캐싱 설정
    # - 디폴트: False (비활성화 - 저장 비용 없음)
    # - True: 암시적 캐싱 활성화 (프롬프트 앞부분에 CAG 메타데이터 주입)
    enable_cag_caching: bool = Field(default=False, alias="ENABLE_CAG_CACHING")

    # CAG 캐시 TTL (Time-To-Live) in minutes
    # 암시적 캐싱 사용: 저장 비용 없음 (리스크 제로)
    # 기본값: 5분
    cag_cache_ttl_minutes: int = Field(default=5, alias="CAG_CACHE_TTL_MINUTES")

    # 기타 설정
    analytics_api_url: Optional[str] = Field(default=None, alias="ANALYTICS_API_URL")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    port: int = Field(default=8004, alias="PORT")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
