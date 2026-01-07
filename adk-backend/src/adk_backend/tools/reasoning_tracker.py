"""
Reasoning Tracker for Conversational Analytics

Provides structured reasoning tracking similar to Sequential Thinking MCP
to expose the AI's decision-making process transparently.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ReasoningStep:
    """Single step in the reasoning process"""
    step_number: int
    phase: str  # 'question_analysis', 'table_selection', 'query_strategy', 'insight_derivation'
    thought: str
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Optional[Dict[str, Any]] = None


class ReasoningTracker:
    """Tracks and structures the reasoning process for conversational analytics"""

    def __init__(self):
        self.steps: List[ReasoningStep] = []
        self.current_step = 0

    def add_step(
        self,
        phase: str,
        thought: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReasoningStep:
        """Add a reasoning step"""
        self.current_step += 1
        step = ReasoningStep(
            step_number=self.current_step,
            phase=phase,
            thought=thought,
            confidence=confidence,
            metadata=metadata or {}
        )
        self.steps.append(step)
        return step

    def add_question_analysis(self, question: str, intent: str, required_data: List[str]) -> ReasoningStep:
        """Track question analysis phase"""
        thought = (
            f"사용자 질문 분석: '{question}'\n"
            f"의도: {intent}\n"
            f"필요 데이터: {', '.join(required_data)}"
        )
        return self.add_step(
            phase="question_analysis",
            thought=thought,
            metadata={
                "question": question,
                "intent": intent,
                "required_data": required_data
            }
        )

    def add_table_selection(
        self,
        selected_tables: List[str],
        reasons: Dict[str, str],
        alternatives_considered: Optional[List[str]] = None
    ) -> ReasoningStep:
        """Track table selection phase"""
        table_reasoning = []
        for table in selected_tables:
            reason = reasons.get(table, "적합한 데이터 포함")
            table_reasoning.append(f"  - {table}: {reason}")

        thought = (
            f"테이블 선정:\n" +
            "\n".join(table_reasoning)
        )

        if alternatives_considered:
            thought += f"\n고려했으나 제외: {', '.join(alternatives_considered)}"

        return self.add_step(
            phase="table_selection",
            thought=thought,
            metadata={
                "selected_tables": selected_tables,
                "reasons": reasons,
                "alternatives_considered": alternatives_considered or []
            }
        )

    def add_query_strategy(
        self,
        strategy_type: str,
        operations: List[str],
        rationale: str
    ) -> ReasoningStep:
        """Track query strategy phase"""
        thought = (
            f"쿼리 전략: {strategy_type}\n"
            f"주요 작업:\n" +
            "\n".join(f"  - {op}" for op in operations) +
            f"\n이유: {rationale}"
        )
        return self.add_step(
            phase="query_strategy",
            thought=thought,
            metadata={
                "strategy_type": strategy_type,
                "operations": operations,
                "rationale": rationale
            }
        )

    def add_insight_derivation(
        self,
        findings: str,
        interpretation: str,
        confidence: float = 1.0
    ) -> ReasoningStep:
        """Track insight derivation phase"""
        thought = (
            f"분석 결과 해석:\n"
            f"발견사항: {findings}\n"
            f"의미: {interpretation}"
        )
        return self.add_step(
            phase="insight_derivation",
            thought=thought,
            confidence=confidence,
            metadata={
                "findings": findings,
                "interpretation": interpretation
            }
        )

    def get_formatted_reasoning(self) -> str:
        """Get formatted reasoning for display"""
        if not self.steps:
            return ""

        formatted = "🧠 **분석 사고 과정**\n\n"

        phase_icons = {
            "question_analysis": "❓",
            "table_selection": "📊",
            "query_strategy": "🎯",
            "insight_derivation": "💡"
        }

        phase_names = {
            "question_analysis": "질문 분석",
            "table_selection": "테이블 선정",
            "query_strategy": "쿼리 전략",
            "insight_derivation": "인사이트 도출"
        }

        for step in self.steps:
            icon = phase_icons.get(step.phase, "•")
            phase_name = phase_names.get(step.phase, step.phase)
            formatted += f"{icon} **{step.step_number}. {phase_name}**\n"
            formatted += f"{step.thought}\n\n"

        return formatted

    def to_dict(self) -> Dict[str, Any]:
        """Convert reasoning to dictionary for API response"""
        return {
            "total_steps": len(self.steps),
            "steps": [
                {
                    "step_number": step.step_number,
                    "phase": step.phase,
                    "thought": step.thought,
                    "confidence": step.confidence,
                    "timestamp": step.timestamp,
                    "metadata": step.metadata
                }
                for step in self.steps
            ]
        }

    def get_summary_list(self) -> List[str]:
        """Get simplified reasoning as list of strings"""
        summary = []

        for step in self.steps:
            phase_emoji = {
                "question_analysis": "❓",
                "table_selection": "📊",
                "query_strategy": "🎯",
                "insight_derivation": "💡"
            }.get(step.phase, "•")

            # Simplify the thought to first line or first 100 chars
            thought_summary = step.thought.split('\n')[0]
            if len(thought_summary) > 100:
                thought_summary = thought_summary[:97] + "..."

            summary.append(f"{phase_emoji} {thought_summary}")

        return summary
