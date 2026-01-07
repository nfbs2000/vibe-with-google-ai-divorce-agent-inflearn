from __future__ import annotations

import os
from typing import Dict

import pytest
from fastapi.testclient import TestClient

from adk_backend.app import app
from adk_backend.tools.bigquery import TEMPLATES, bigquery_render_template

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")


client = TestClient(app)


def test_list_templates_returns_known_template() -> None:
    response = client.get("/api/templates")
    assert response.status_code == 200
    data = response.json()
    templates = data.get("templates") or []
    assert any(t.get("id") == "smishing_daily_counts" for t in templates)
    assert any(t.get("id") == "fcm_threat_level_summary" for t in templates)
    assert any(t.get("id") == "malicious_app_top_packages" for t in templates)
    assert any(t.get("id") == "security_conversion_summary" for t in templates)
    assert any(t.get("id") == "marketing_segment_performance" for t in templates)


def test_render_template_uses_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = {"template_id": "demo", "sql": "SELECT 1"}

    def fake_render(template_id: str, params: Dict, dry_run: bool = False, project_id=None):
        assert template_id == "smishing_daily_counts"
        return {**stub, "params": params or {}}

    monkeypatch.setattr("adk_backend.app.bigquery_render_template", fake_render)

    response = client.post(
        "/api/templates/render",
        json={
            "template_id": "smishing_daily_counts",
            "params": {"project_id": "proj", "dataset_id": "data", "table": "smishing_talks"},
        },
    )
    assert response.status_code == 200
    assert response.json()["sql"] == "SELECT 1"


def test_render_template_warns_when_limit_missing() -> None:
    template_id = "tmp_no_limit"
    TEMPLATES[template_id] = {
        "label": "LIMIT 없는 테스트",
        "description": "경고 테스트용 템플릿",
        "required_params": ["start_date"],
        "sql": (
            """
            SELECT user_pseudo_id
            FROM `{project_id}.{dataset_id}.{table}`
            WHERE event_date = '{start_date}'
            """
        ),
        "defaults": {"table": "events_*"},
    }
    try:
        rendered = bigquery_render_template(
            template_id,
            params={"project_id": "demo-project", "dataset_id": "analytics_test", "start_date": "20241101"},
        )
        warnings = rendered.get("warnings") or []
        assert any("LIMIT" in warning for warning in warnings)
    finally:
        TEMPLATES.pop(template_id, None)


def test_modern_templates_render() -> None:
    smishing = bigquery_render_template(
        "smishing_daily_counts",
        params={
            "project_id": "demo-project",
            "dataset_id": "analytics_test",
            "table": "smishing_talks",
            "lookback_days": 14,
        },
    )
    assert "smishing_events" in smishing["sql"]

    marketing = bigquery_render_template(
        "marketing_segment_performance",
        params={
            "project_id": "demo-project",
            "dataset_id": "analytics_test",
            "lookback_days": 30,
        },
    )
    assert "segment_name" in marketing["sql"]


def test_render_template_blocks_dangerous_keywords() -> None:
    template_id = "tmp_delete"
    TEMPLATES[template_id] = {
        "label": "위험 SQL 테스트",
        "description": "금지 키워드 감지 테스트",
        "required_params": ["start_date"],
        "sql": (
            """
            DELETE FROM `{project_id}.{dataset_id}.{table}`
            WHERE event_date = '{start_date}'
            """
        ),
        "defaults": {"table": "events_*"},
    }
    try:
        with pytest.raises(ValueError):
            bigquery_render_template(
                template_id,
                params={"project_id": "demo-project", "dataset_id": "analytics_test", "start_date": "20241101"},
            )
    finally:
        TEMPLATES.pop(template_id, None)
