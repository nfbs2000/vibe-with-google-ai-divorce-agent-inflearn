import os
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from .gemini_client import GeminiClient
from .prompt_templates import PromptType

logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    """AI 모델 제공자 정의"""
    GEMINI = "gemini"

class AIClient:
    """통합 AI 클라이언트 - Gemini 모델 전용"""

    def __init__(self,
                 gemini_model: str = "gemini-2.5-flash"):
        """
        AI 클라이언트 초기화

        Args:
            gemini_model: Gemini 모델명
        """
        # Gemini 클라이언트만 초기화
        self.gemini_client = GeminiClient(model=gemini_model)
        self.current_provider = "gemini"

        if not self.gemini_client.is_available():
            logger.error("Gemini API not available")
            self.current_provider = "none"

        logger.info(f"AI Client initialized with Gemini: {self.current_provider}")

    def get_current_client(self) -> Optional[GeminiClient]:
        """현재 활성 클라이언트 반환 (Gemini만)"""
        if self.current_provider == "gemini":
            return self.gemini_client
        return None

    def is_available(self) -> bool:
        """AI 서비스 사용 가능 여부 확인"""
        return self.current_provider == "gemini" and self.gemini_client.is_available()

    def get_provider_status(self) -> Dict[str, Any]:
        """제공자 상태 정보 반환"""
        return {
            "current_provider": self.current_provider,
            "default_provider": "gemini",
            "providers": {
                "gemini": {
                    "available": self.gemini_client.is_available(),
                    "model": self.gemini_client.model_name if self.gemini_client.is_available() else None
                }
            }
        }

    async def generate_completion(
        self,
        prompt_type: PromptType, 
        **kwargs
    ) -> Optional[str]:
        """현재 활성 제공자를 사용하여 완성 생성"""
        client = self.get_current_client()
        if not client:
            logger.error("No AI client available for completion generation")
            return None
        
        return await client.generate_completion(prompt_type, **kwargs)
    
    def interpret_result(
        self, 
        query: str, 
        sql: str, 
        result: List[Dict[str, Any]]
    ) -> Optional[str]:
        """결과 해석"""
        client = self.get_current_client()
        if not client:
            logger.error("No AI client available for result interpretation")
            return None
        
        return client.interpret_result(query, sql, result)
    
    def recommend_chart(
        self, 
        query: str, 
        columns: List[str], 
        data_types: List[str]
    ) -> Optional[Dict[str, str]]:
        """차트 추천"""
        client = self.get_current_client()
        if not client:
            logger.error("No AI client available for chart recommendation")
            return None
        
        result = client.recommend_chart(query, columns, data_types)
        if result:
            result["provider"] = self.current_provider
        return result

# 전역 통합 AI 클라이언트 인스턴스 (지연 초기화)
ai_client = None

from ..config import get_settings

def get_ai_client() -> AIClient:
    """AI 클라이언트 인스턴스 반환 (지연 초기화)"""
    global ai_client
    if ai_client is None:
        settings = get_settings()
        ai_client = AIClient(gemini_model=settings.adk_model_name)
    return ai_client
