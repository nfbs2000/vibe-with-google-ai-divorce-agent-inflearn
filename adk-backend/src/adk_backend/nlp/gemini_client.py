import os
import json
from typing import Dict, List, Optional, Any
import logging
import google.generativeai as genai
from google.cloud import bigquery
from .prompt_templates import PromptType, PromptTemplate

logger = logging.getLogger(__name__)

class GeminiClient:
    """Google Gemini API 클라이언트 클래스"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash", cag_metadata: Optional[str] = None, enable_cag_caching: bool = False, cag_cache_ttl_minutes: int = 60):
        """
        Gemini 클라이언트 초기화

        Args:
            api_key: Google API 키 (환경변수에서 자동 로드)
            model: 사용할 모델명
            cag_metadata: Context Cache용 판례 메타데이터 JSON (middleware에서 주입)
            enable_cag_caching: 암시적 캐싱 활성화 여부 (기본값: False)
            cag_cache_ttl_minutes: CAG 캐시 TTL in minutes (기본값: 60)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model_name = model
        self.cag_metadata = cag_metadata if enable_cag_caching else None  # 캐싱 비활성화 시 메타데이터 미주입
        self.enable_cag_caching = enable_cag_caching  # 암시적 캐싱 활성화 여부
        self.cag_cache_ttl_minutes = cag_cache_ttl_minutes  # 캐시 TTL (분)

        if not self.api_key:
            logger.warning("Google API key not found. Some features will be limited.")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)

        self.prompt_templates = self._load_prompt_templates()
        self.bq_client = bigquery.Client() if self._should_init_bq() else None

    def _should_init_bq(self) -> bool:
        """BigQuery 클라이언트 초기화 가능 여부 확인"""
        try:
            # 간단한 test: BigQuery 클라이언트 생성 가능한지 확인
            client = bigquery.Client()
            client.get_dataset("divorce_analytics")
            return True
        except Exception as e:
            logger.warning(f"BigQuery client initialization failed: {e}")
            return False


    def _load_prompt_templates(self) -> Dict[PromptType, PromptTemplate]:
        """프롬프트 템플릿 로드"""
        templates = {
            PromptType.INTENT_ANALYSIS: PromptTemplate(
                name="이혼 상담 의도 분석",
                system_message="""
당신은 이혼 소송 관련 자연어 질의를 분석하여 사용자의 의도를 파악하는 전문가입니다.
사용자의 질문을 분석하여 다음 중 하나의 의도로 분류해주세요:

- COUNT: 판례 개수를 세는 질문 (예: '부정행위 판례가 몇 개인가요?')
- AGGREGATE: 위자료 평균, 재산분할 비율 등 집계 (예: '평균 위자료는 얼마인가요?')
- FILTER: 특정 조건(유책 사유 등)으로 데이터 필터링
- TREND: 시기별 이혼 추세 분석
- COMPARISON: 유책 사유별 위자료 비교 또는 기간 비교
- SEARCH: 특정 키워드나 태그가 포함된 판례 검색
- RANKING: 위자료 액수 기준 상위 판례 등
- DISTRIBUTION: 위자료 액수대별 분포 분석

응답은 반드시 JSON 형식으로 해주세요: {"intent": "INTENT_NAME", "confidence": 0.95}
""",
                user_template="다음 이혼 관련 질문의 의도를 분석해주세요: {query}",
                examples=[
                    {
                        "input": "부정행위로 인한 위자료 평균이 얼마인가요?",
                        "output": '{"intent": "AGGREGATE", "confidence": 0.98}'
                    },
                    {
                        "input": "최근 1년간 폭언 관련 판례를 모두 찾아주세요",
                        "output": '{"intent": "FILTER", "confidence": 0.95}'
                    }
                ],
                max_tokens=100,
                temperature=0.1
            ),
            
            PromptType.ENTITY_EXTRACTION: PromptTemplate(
                name="이혼 상담 엔티티 추출",
                system_message="""
당신은 이혼 소송 질의에서 분석에 필요한 주요 정보를 추출하는 전문가입니다.
다음 정보를 추출하여 JSON으로 응답해주세요:

1. table: 항상 'precedent_cases' 고정
2. fault_type: 유책 사유 (예: '부정행위', '폭언', '도박', '고부갈등' 등)
3. alimony_range: 위자료 범위 (예: '2000만원 이상', '3000만원 미만')
4. property_ratio: 재산분할 비율 관련 키워드
5. time_period: 분석 기간 (예: '최근 3년', '2023년 이후')
6. aggregation: 사용할 집계 함수 (COUNT, AVG_ALIMONY, AVG_PROPERTY_RATIO 등)

응답 예시: {"table": "precedent_cases", "fault_type": "부정행위", "aggregation": "AVG_ALIMONY"}
""",
                user_template="다음 질문에서 엔티티를 추출해주세요: {query}",
                examples=[
                    {
                        "input": "상간녀 소송 시 위자료는 보통 얼마나 나오나요?",
                        "output": '{"table": "precedent_cases", "fault_type": "부정행위", "aggregation": "AVG_ALIMONY"}'
                    }
                ],
                max_tokens=200,
                temperature=0.1
            ),

            PromptType.RESULT_INTERPRETATION: PromptTemplate(
                name="결과 해석",
                system_message="""
당신은 데이터 분석 결과를 한국어로 자연스럽게 해석하는 전문가입니다.
SQL 쿼리 결과를 사용자가 이해하기 쉽게 설명해주세요.

규칙:
- 한국어로 자연스럽게 설명
- 숫자는 천 단위 구분자 사용
- 중요한 인사이트나 패턴 강조
- 간결하고 명확하게 작성
""",
                user_template="질문: {query}\nSQL: {sql}\n결과: {result}\n\n위 결과를 자연스럽게 해석해주세요.",
                examples=[],
                max_tokens=300,
                temperature=0.3
            ),
            
            PromptType.CHART_RECOMMENDATION: PromptTemplate(
                name="차트 추천",
                system_message="""
당신은 데이터 시각화 전문가입니다. 쿼리 결과에 가장 적합한 차트 타입을 추천해주세요.

사용 가능한 차트 타입:
- bar: 카테고리별 비교
- line: 시간에 따른 변화
- pie: 전체에서 각 부분의 비율
- table: 상세 데이터 표시

응답은 반드시 JSON 형식으로 해주세요: {"chart_type": "bar", "reason": "이유"}
""",
                user_template="질문: {query}\n결과 컬럼: {columns}\n데이터 타입: {data_types}\n\n가장 적합한 차트를 추천해주세요.",
                examples=[],
                max_tokens=150,
                temperature=0.2
            )
        }
        
        return templates
    
    def is_available(self) -> bool:
        """Gemini API 사용 가능 여부 확인"""
        return self.model is not None

    def get_caching_status(self) -> Dict[str, Any]:
        """
        CAG 암시적 캐싱 상태 조회 (모니터링용)

        Returns:
            캐싱 설정 및 상태 정보 딕셔너리
        """
        return {
            "caching_enabled": self.enable_cag_caching,
            "cache_ttl_minutes": self.cag_cache_ttl_minutes,
            "cag_metadata_loaded": self.cag_metadata is not None,
            "cag_metadata_size_bytes": len(self.cag_metadata) if self.cag_metadata else 0,
        }

    def _collect_response_text(self, response: Any, context: str) -> Optional[str]:
        """Gemini 응답에서 텍스트를 안전하게 추출"""
        if not response:
            logger.warning("Gemini response is empty for %s", context)
            return None

        # 방법 1: response.text 속성 사용 (가장 간단)
        try:
            if hasattr(response, 'text'):
                text = response.text
                if text:
                    logger.info(f"[{context}] Successfully extracted text using response.text: {text[:100]}...")
                    return text.strip()
                else:
                    logger.warning(f"[{context}] response.text exists but is empty")
        except Exception as e:
            logger.warning(f"[{context}] Failed to access response.text: {e}")

        # 방법 2: candidates 구조 사용 (fallback)
        logger.info(f"[{context}] Trying fallback method via candidates")
        candidates = getattr(response, "candidates", None)
        if not candidates:
            logger.warning(f"[{context}] No candidates found. Response type: {type(response)}, dir: {dir(response)[:10]}...")
            return None

        logger.info(f"[{context}] Found {len(candidates)} candidate(s)")

        candidate = candidates[0]
        finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
        logger.info(f"[{context}] Finish reason: {finish_reason}")

        content = getattr(candidate, "content", None)
        if not content:
            logger.warning(f"[{context}] No content in candidate. Candidate type: {type(candidate)}, dir: {dir(candidate)[:10]}...")
            return None

        logger.info(f"[{context}] Content found: {type(content)}")

        parts = getattr(content, "parts", None)
        if parts is None:
            logger.warning(f"[{context}] Parts is None. Content type: {type(content)}, dir: {dir(content)[:10]}...")
            return None

        if not parts:  # Empty list
            logger.warning(f"[{context}] Parts list is empty (length: {len(parts)})")
            return None

        logger.info(f"[{context}] Found {len(parts)} part(s)")

        collected_parts: List[str] = []
        for i, part in enumerate(parts):
            text = getattr(part, "text", None)
            logger.info(f"[{context}] Part {i}: text length = {len(text) if text else 0}")
            if text:
                collected_parts.append(text)

        if not collected_parts:
            logger.warning(f"[{context}] No text found in any parts")
            return None

        result = "".join(collected_parts).strip()
        logger.info(f"[{context}] Successfully extracted {len(result)} characters")
        return result
    
    def _format_prompt_for_gemini(self, system_message: str, user_message: str, examples: List[Dict[str, str]] = None) -> str:
        """Gemini용 프롬프트 포맷팅"""
        prompt = f"{system_message}\n\n"
        
        if examples:
            prompt += "예시:\n"
            for example in examples:
                prompt += f"입력: {example['input']}\n출력: {example['output']}\n\n"
        
        prompt += f"질문: {user_message}\n답변:"
        return prompt
    
    async def generate_completion(
        self, 
        prompt_type: PromptType, 
        **kwargs
    ) -> Optional[str]:
        """
        Gemini API를 사용하여 완성 생성
        
        Args:
            prompt_type: 프롬프트 타입
            **kwargs: 프롬프트 템플릿에 전달할 변수들
            
        Returns:
            생성된 텍스트 또는 None (API 사용 불가시)
        """
        if not self.is_available():
            logger.warning(f"Gemini API not available for {prompt_type.value}")
            return None
            
        try:
            template = self.prompt_templates[prompt_type]
            user_message = template.user_template.format(**kwargs)
            
            prompt = self._format_prompt_for_gemini(
                template.system_message, 
                user_message, 
                template.examples
            )
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=template.max_tokens,
                temperature=template.temperature
            )

            # 안전 설정 완화 (데이터 분석/쿼리 생성 목적)
            safety_settings = {
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            result_text = self._collect_response_text(response, prompt_type.value)
            if not result_text:
                return None
            logger.info(f"Gemini API call successful for {prompt_type.value}")
            return result_text

        except Exception as e:
            logger.error(f"Gemini API call failed for {prompt_type.value}: {str(e)}")
            return None
    
    def interpret_result(
        self, 
        query: str, 
        sql: str, 
        result: List[Dict[str, Any]]
    ) -> Optional[str]:
        """결과 해석 (동기 버전)"""
        if not self.is_available():
            return None
            
        try:
            template = self.prompt_templates[PromptType.RESULT_INTERPRETATION]
            serialized_result = json.dumps(result[:5], ensure_ascii=False)
            serialized_result = serialized_result.replace('{', '{{').replace('}', '}}')

            user_message = template.user_template.format(
                query=query,
                sql=sql,
                result=serialized_result  # 처음 5개 행만 전달
            )
            
            prompt = self._format_prompt_for_gemini(
                template.system_message, 
                user_message
            )
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=template.max_tokens,
                temperature=template.temperature
            )

            # 안전 설정 완화 (데이터 분석/쿼리 생성 목적)
            safety_settings = {
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            return self._collect_response_text(response, "result_interpretation")
            
        except Exception as e:
            logger.error(f"Result interpretation failed: {str(e)}")
            return None
    
    def recommend_chart(
        self, 
        query: str, 
        columns: List[str], 
        data_types: List[str]
    ) -> Optional[Dict[str, str]]:
        """차트 추천 (동기 버전)"""
        if not self.is_available():
            return None
            
        try:
            template = self.prompt_templates[PromptType.CHART_RECOMMENDATION]
            user_message = template.user_template.format(
                query=query,
                columns=columns,
                data_types=data_types
            )
            
            prompt = self._format_prompt_for_gemini(
                template.system_message, 
                user_message
            )
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=template.max_tokens,
                temperature=template.temperature
            )

            # 안전 설정 완화 (데이터 분석/쿼리 생성 목적)
            safety_settings = {
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            result = self._collect_response_text(response, "chart_recommendation")
            if not result:
                return None
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from Gemini response: {result}")
                return {"chart_type": "table", "reason": "기본 테이블 형식"}
            
        except Exception as e:
            logger.error(f"Chart recommendation failed: {str(e)}")
            return None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        텍스트 임베딩 생성 (text-embedding-004)
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            임베딩 벡터 (float 리스트) 또는 None
        """
        if not self.is_available():
            logger.warning("Gemini API not available for embeddings")
            return None

        try:
            # 줄바꿈 등 전처리
            text = text.replace("\n", " ")
            
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
                title="Embedding of court case"
            )
            
            if 'embedding' in result:
                return result['embedding']
            else:
                logger.warning("No embedding in result")
                return None
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            return None

# 전역 Gemini 클라이언트 인스턴스 (lazy initialization with CAG)
_gemini_client_instance = None
_cag_metadata = None


def initialize_gemini_client_with_cag(cag_metadata: Optional[str] = None) -> GeminiClient:
    """
    CAG 메타데이터를 로드하여 Gemini 클라이언트 초기화

    암시적 캐싱(Implicit Caching)만 사용:
    - 저장 비용 없음 (리스크 제로)
    - ENABLE_CAG_CACHING 환경 변수로 활성화/비활성화 가능
    - 기본값: 비활성화 (False)

    Args:
        cag_metadata: CAG 메타데이터 (없으면 middleware에서 자동 로드)

    Returns:
        초기화된 GeminiClient 인스턴스
    """
    global _gemini_client_instance, _cag_metadata
    from ..config import get_settings

    if _gemini_client_instance is not None:
        logger.warning("Gemini 클라이언트가 이미 초기화되었습니다.")
        return _gemini_client_instance

    # 설정에서 캐싱 활성화 여부 및 TTL 읽기
    settings = get_settings()
    enable_caching = settings.enable_cag_caching
    ttl_minutes = settings.cag_cache_ttl_minutes

    logger.info(f"📦 CAG 암시적 캐싱 설정: {'✅ 활성화' if enable_caching else '❌ 비활성화 (저장 비용 없음)'}")
    if enable_caching:
        logger.info(f"⏱️ CAG 캐시 TTL: {ttl_minutes}분")

    # 캐싱 활성화 시에만 메타데이터 로드
    if enable_caching:
        if cag_metadata is None:
            from ..middleware.precedent_cag_loader import load_precedent_cag
            cag_metadata = load_precedent_cag()
            if cag_metadata is None:
                logger.warning("CAG 메타데이터 로드 실패. 캐싱이 비활성화됩니다.")
                cag_metadata = ""
        _cag_metadata = cag_metadata
        logger.info(f"✅ CAG 메타데이터 로드 완료 (크기: {len(cag_metadata)} 바이트, TTL: {ttl_minutes}분)")
    else:
        # 캐싱 비활성화 시 메타데이터 로드하지 않음
        logger.info("⏭️ CAG 메타데이터 로드 스킵 (캐싱 비활성화)")
        cag_metadata = None
        _cag_metadata = None

    _gemini_client_instance = GeminiClient(
        cag_metadata=cag_metadata,
        enable_cag_caching=enable_caching,
        cag_cache_ttl_minutes=ttl_minutes
    )

    logger.info("✅ Gemini 클라이언트 초기화 완료")
    return _gemini_client_instance


def get_gemini_client() -> GeminiClient:
    """
    Gemini 클라이언트 싱글톤 인스턴스 반환

    CAG 메타데이터는 앱 시작시 initialize_gemini_client_with_cag()로 초기화됩니다.
    암시적 캐싱 활성화 여부는 ENABLE_CAG_CACHING 환경 변수로 제어합니다.
    """
    global _gemini_client_instance

    if _gemini_client_instance is None:
        # 백업: 직접 초기화 (권장하지 않음, app lifespan에서 initialize_gemini_client_with_cag() 호출 필요)
        from ..config import get_settings
        settings = get_settings()
        logger.warning(
            "⚠️  Gemini 클라이언트를 직접 초기화합니다. "
            "app.py의 lifespan에서 initialize_gemini_client_with_cag()을 호출하는 것이 권장됩니다."
        )
        _gemini_client_instance = GeminiClient(
            cag_metadata=None,
            enable_cag_caching=settings.enable_cag_caching,
            cag_cache_ttl_minutes=settings.cag_cache_ttl_minutes
        )

    return _gemini_client_instance
