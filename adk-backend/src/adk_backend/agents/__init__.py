"""
Agents module - 에이전트 모듈

구조:
- domain experts: 도메인 전문가 에이전트 (이혼 관련)
- registry: 에이전트 레지스트리
"""

# Domain expert agent
from .divorce_case_domain_expert import divorce_case_agent

# Domain router and registry
from .registry import AGENT_REGISTRY, AgentInfo, get_active_agents, get_agent_info

__all__ = [
    # Main Unified Agent
    "divorce_case_agent",
    # Registry
    "AGENT_REGISTRY",
    "AgentInfo",
    "get_active_agents",
    "get_agent_info",
]
