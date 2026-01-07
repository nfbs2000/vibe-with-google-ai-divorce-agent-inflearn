from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from google.adk.agents import Agent

# Domain expert agents
from .divorce_case_domain_expert import divorce_case_agent


@dataclass(frozen=True)
class AgentInfo:
    """에이전트 메타데이터와 실제 Agent 인스턴스를 묶어서 관리."""

    key: str
    display_name: str
    description: str
    agent: Agent
    focus: str
    keywords: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    active: bool = True


AGENT_REGISTRY: Dict[str, AgentInfo] = {
    "divorce_case": AgentInfo(
        key="divorce_case",
        display_name="통합 이혼 솔루션 전문가",
        description="멀티모달 증거 분석, 판례 검색, 자연어 통계 분석을 모두 수행하는 통합 에이전트",
        agent=divorce_case_agent,
        focus="이혼 상담 및 법적/데이터 분석",
        keywords=[
            "이혼",
            "증거",
            "판례",
            "유책배우자",
            "민법840조",
            "위자료",
            "재산분할",
            "부정행위",
            "상간녀",
            "자연어",
            "대화",
            "인사이트",
            "AI분석",
            "탐색",
            "요약",
            "질문",
        ],
        strengths=[
            "Gemini Files API 멀티모달 분석 (이미지/PDF)",
            "61개 핵심 판례 기반 정밀 RAG 검색",
            "SQL 없이 자연어로 BigQuery 판례 데이터 탐색",
            "민법 제840조 기반 법적 판단 지원",
            "변호사 상담 자료 자동 생성",
        ],
        active=True,
    ),
}


def get_active_agents() -> List[AgentInfo]:
    """UI에서 노출 가능한 활성화된 에이전트 목록."""
    return [info for info in AGENT_REGISTRY.values() if info.active]


def get_agent_info(key: str) -> AgentInfo:
    """에이전트 키로 AgentInfo 조회."""
    return AGENT_REGISTRY[key]
