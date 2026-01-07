"""
Gemini File Search Tool for Precedent Documents

Provides document search capabilities using Gemini File Search API.
This tool searches the entire File Search Store by store_name only.
It does NOT support per-file targeting or file_id filtering.
"""
import os
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class PrecedentSearchTool:
    """
    판례 문서 Gemini File Search API 도구
    - store_name 단위 전체 검색만 지원
    - file_id/부분집합 필터링은 지원하지 않음

    Use Cases:
    - 위자료 관련 판례 검색
    - 재산분할 판례 검색
    - 이혼 사유별 판례 검색
    - 판례 분석 및 사례 참조

    Example:
        tool = PrecedentSearchTool()
        result = tool.search("위자료 월 500만원 판례")
        print(result["answer"])
    """

    def __init__(self, store_name: Optional[str] = None, model: str = "gemini-2.5-flash"):
        """
        Initialize Precedent Search Tool

        Args:
            store_name: File Search Store 이름 (판례 전용, 환경변수에서 로드)
            model: Gemini 모델 (기본값: gemini-2.5-flash, File Search 지원 필수)
        """
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY 환경변수가 필요합니다")

        self.store_name = store_name or os.getenv("PRECEDENT_FILE_SEARCH_STORE_NAME")
        if not self.store_name:
            raise ValueError("PRECEDENT_FILE_SEARCH_STORE_NAME이 설정되지 않았습니다")

        self.model = model
        self.client = None  # Lazy initialization

        logger.info(f"PrecedentSearchTool initialized: store={self.store_name}, model={self.model}")

    def _get_client(self):
        """Lazy load Gemini client"""
        if self.client is None:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        return self.client

    def search(
        self,
        query: str,
        max_results: int = 3,
        include_citations: bool = True
    ) -> Dict[str, Any]:
        """
        판례 문서 검색 (영구 스토리지, store_name 전체 검색)

        Args:
            query: 검색 질의
            max_results: 최대 결과 수 (Citations 개수)
            include_citations: Citation 포함 여부

        Returns:
            {
                "answer": str,  # 검색 결과 답변
                "citations": [  # 출처 정보 (include_citations=True인 경우)
                    {
                        "source": str,  # 파일명
                        "content": str,  # 인용된 내용
                        "fileSearchStore": str  # 저장소 정보
                    }
                ],
                "model": str,  # 사용된 모델
                "store": str  # 검색된 스토어명
            }
        """
        try:
            import requests

            # REST API 엔드포인트 (v1beta/models:generateContent)
            # File Search Store를 통한 영구 스토리지 검색
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

            # Request payload - 영구 스토리지 File Search Store 지정
            payload = {
                "contents": [{
                    "parts": [{"text": query}]
                }],
                "tools": [{
                    "file_search": {
                        "file_search_store_names": [self.store_name]
                    }
                }],
                "system_instruction": (
                    "당신은 판례 분석 전문가입니다. "
                    "제공된 판례 문서를 바탕으로 정확하고 객관적인 답변을 제공하세요. "
                    "출처 정보(판례명, 사건번호, 선고일자)를 명확히 표시하세요."
                )
            }

            # API 호출
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                params={"key": self.api_key},
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            # 답변 추출
            answer = ""
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        answer = parts[0]["text"]

            # Citations 추출 (영구 스토리지 파일 정보)
            citations = []
            if include_citations and "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                # File Search Store의 groundingMetadata 추출
                if "groundingMetadata" in candidate:
                    grounding = candidate["groundingMetadata"]
                    if "groundingChunks" in grounding:
                        for chunk in grounding["groundingChunks"][:max_results]:
                            citation = {}

                            # retrievedContext에서 정보 추출
                            if "retrievedContext" in chunk:
                                context = chunk["retrievedContext"]
                                if "title" in context:
                                    citation["source"] = context["title"]
                                if "text" in context:
                                    citation["content"] = context["text"]
                                if "fileSearchStore" in context:
                                    # 영구 스토리지 정보 명시
                                    citation["fileSearchStore"] = context["fileSearchStore"]

                            if citation:
                                citations.append(citation)

            result = {
                "answer": answer,
                "citations": citations,
                "model": self.model,
                "store": self.store_name,  # 사용된 스토어명 명시
                "source": "permanent_file_search_store"  # 영구 저장소 표시
            }

            logger.info(
                f"Precedent Search success: "
                f"query='{query[:50]}...', "
                f"store='{self.store_name}', "
                f"citations={len(citations)}"
            )
            return result

        except Exception as e:
            logger.error(f"Precedent Search failed: store='{self.store_name}', error={e}")
            return {
                "answer": f"판례 검색 중 오류 발생: {str(e)}",
                "citations": [],
                "model": self.model,
                "store": self.store_name,
                "error": str(e),
                "source": "error"
            }

    def format_response(self, result: Dict[str, Any]) -> str:
        """
        검색 결과를 포맷팅 (영구 스토리지 정보 포함)

        Args:
            result: search() 메서드의 반환값

        Returns:
            포맷팅된 응답 문자열
        """
        output = result['answer']

        # 영구 스토리지 정보 표시
        if result.get('source') == 'permanent_file_search_store':
            output += f"\n\n🔒 **저장소**: 영구 File Search Store\n"
            output += f"   📦 {result.get('store', 'Unknown')}\n"

        # Citations 추가 (판례 출처)
        if result.get('citations'):
            output += "\n\n📚 **관련 판례**:\n"
            for i, citation in enumerate(result['citations'], 1):
                source = citation.get('source', 'Unknown')
                content = citation.get('content', '')

                # Content 요약 (최대 150자)
                content_preview = content[:150] + "..." if len(content) > 150 else content

                output += f"{i}. **{source}**\n"
                if content_preview:
                    output += f"   > {content_preview}\n"

                # File Search Store 정보
                if citation.get('fileSearchStore'):
                    output += f"   📦 {citation.get('fileSearchStore')}\n"

        return output

    def get_tool_definition(self) -> Dict[str, Any]:
        """
        ADK Tool 정의 반환

        Returns:
            Tool definition for ADK agent registration
        """
        return {
            "name": "precedent_search",
            "description": (
                "판례 문서 검색 도구. "
                "store_name 단위로 전체 문서를 검색합니다. "
                "file_id로 특정 파일만 검색하는 기능은 지원하지 않습니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색할 질의 (예: '위자료 월 500만원', '재산분할 50대50', '부정행위 이혼')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "최대 결과 수 (기본값: 3)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }


# Tool 인스턴스 (싱글톤)
_precedent_search_tool = None


def get_precedent_search_tool() -> PrecedentSearchTool:
    """
    PrecedentSearchTool 싱글톤 인스턴스 반환

    Returns:
        PrecedentSearchTool instance
    """
    global _precedent_search_tool
    if _precedent_search_tool is None:
        _precedent_search_tool = PrecedentSearchTool()
    return _precedent_search_tool


def search_precedents(query: str, max_results: int = 3) -> str:
    """
    판례 검색 함수 (ADK Tool wrapper)
    - store_name 기반 전체 검색만 수행합니다.
    - file_id로 특정 문서를 제한하는 기능은 없습니다.

    Args:
        query: 검색 질의 (예: '위자료', '재산분할', '이혼 사유')
        max_results: 최대 결과 수

    Returns:
        포맷팅된 검색 결과
    """
    tool = get_precedent_search_tool()
    result = tool.search(query, max_results)
    return tool.format_response(result)
