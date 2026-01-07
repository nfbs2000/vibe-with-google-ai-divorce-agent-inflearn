"""
Config 테스트

환경 변수 기반 설정 로딩 및 ADK 모델 설정 테스트
"""
from __future__ import annotations

import os

import pytest

from adk_backend.config import Settings, get_settings


def test_adk_model_defaults():
    """ADK 모델 기본값 테스트"""
    settings = Settings(
        GOOGLE_CLOUD_PROJECT="test-project"
    )

    # Gemini 3.0 Pro Preview가 기본값
    assert settings.adk_model_name == "gemini-3-pro-preview-11-2025"
    assert settings.adk_model_region == "us-central1"
    assert settings.adk_model_endpoint == "us-central1-aiplatform.googleapis.com"


def test_adk_model_from_env(monkeypatch: pytest.MonkeyPatch):
    """환경 변수에서 ADK 모델 설정 로딩"""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("ADK_MODEL_NAME", "gemini-2.0-flash-exp")
    monkeypatch.setenv("ADK_MODEL_REGION", "asia-northeast3")
    monkeypatch.setenv("ADK_MODEL_ENDPOINT", "asia-northeast3-aiplatform.googleapis.com")

    settings = Settings()

    assert settings.adk_model_name == "gemini-2.0-flash-exp"
    assert settings.adk_model_region == "asia-northeast3"
    assert settings.adk_model_endpoint == "asia-northeast3-aiplatform.googleapis.com"


def test_file_search_store_name(monkeypatch: pytest.MonkeyPatch):
    """File Search Store 설정 테스트"""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("FILE_SEARCH_STORE_NAME", "fileSearchStores/test-store")

    settings = Settings()

    assert settings.file_search_store_name == "fileSearchStores/test-store"


def test_file_search_store_name_optional(monkeypatch: pytest.MonkeyPatch):
    """File Search Store는 선택적 설정"""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.delenv("FILE_SEARCH_STORE_NAME", raising=False)

    settings = Settings()

    assert settings.file_search_store_name is None


def test_bigquery_settings():
    """BigQuery 설정 테스트"""
    settings = Settings(
        GOOGLE_CLOUD_PROJECT="test-project",
        BIGQUERY_DATASET="analytics_test",
        BIGQUERY_LOCATION="asia-northeast3"
    )

    assert settings.bigquery_dataset == "analytics_test"
    assert settings.bigquery_location == "asia-northeast3"


def test_settings_singleton(monkeypatch: pytest.MonkeyPatch):
    """get_settings는 싱글톤 패턴"""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

    # Clear the cache first
    get_settings.cache_clear()

    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2
