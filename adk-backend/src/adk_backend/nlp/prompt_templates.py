"""
프롬프트 템플릿 정의 - Gemini AI 전용
"""
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum


class PromptType(Enum):
    """프롬프트 타입 정의"""
    INTENT_ANALYSIS = "intent_analysis"
    ENTITY_EXTRACTION = "entity_extraction"
    RESULT_INTERPRETATION = "result_interpretation"
    CHART_RECOMMENDATION = "chart_recommendation"


@dataclass
class PromptTemplate:
    """프롬프트 템플릿 클래스"""
    name: str
    system_message: str
    user_template: str
    examples: List[Dict[str, str]]
    max_tokens: int = 1000
    temperature: float = 0.1
