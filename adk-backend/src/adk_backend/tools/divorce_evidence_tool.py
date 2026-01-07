"""
Divorce Evidence Analysis Tool using Gemini Files API
강좌 Chapter 3에서 다루는 멀티모달 증거 분석 도구입니다.

- 파일을 업로드해 OCR/요약/법적 관련성 판단을 수행합니다.
- 업로드된 파일은 다운로드할 수 없으며, 결과는 분석 JSON만 반환됩니다.
"""
import os
import logging
from typing import List, Dict, Optional, Any
import json
import time
from .bigquery import bigquery_execute

logger = logging.getLogger(__name__)

# 분석할 수 있는 증거 타입 정의
EVIDENCE_TYPES = {
    "image": ["jpg", "jpeg", "png", "webp", "heic"],
    "audio": ["mp3", "wav", "aac", "flac"],
    "document": ["pdf"]
}

class DivorceEvidenceAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found. Some functionality may be limited.")
            
        self.client = None # Lazy load
        self.model = "gemini-2.0-flash" # 멀티모달에 강한 최신 모델

    def _get_client(self):
        if self.client is None:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        return self.client

    def analyze_single_evidence(
        self,
        file_path: str,
        evidence_type: str,
        analysis_focus: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        단일 파일(이미지/오디오/PDF)을 Gemini Files API로 업로드하고 분석합니다.
        반환값은 JSON 분석 결과이며, 파일 다운로드 링크를 제공하지 않습니다.
        """
        client = self._get_client()
        
        # 1. Upload File
        logger.info(f"Uploading file for analysis: {file_path}")
        try:
            file = client.files.upload(file=file_path)
            logger.info(f"File uploaded: {file.name} ({file.uri})")
            # NOTE: Gemini Files API는 업로드한 원본을 다시 다운로드할 수 없습니다.
            # file.name/uri는 분석 컨텍스트 식별용이며 다운로드 링크가 아닙니다.
            # 실제 원본은 별도의 스토리지에 반드시 보관해야 합니다.
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return {"error": str(e)}

        # Wait for processing (Audio/Video needs time)
        while file.state.name == "PROCESSING":
            time.sleep(1)
            file = client.files.get(name=file.name)

        if file.state.name == "FAILED":
            return {"error": "File processing failed by Gemini"}

        # 2. Build Prompt
        focus = ", ".join(analysis_focus) if analysis_focus else "전반적인 내용 분석 및 법적 유효성 평가"
        
        prompt = f"""
        당신은 이혼 소송 전문 증거 분석가입니다.
        주어진 파일({evidence_type})을 분석하여 다음 항목을 도출하세요.
        
        **분석 초점**: {focus}
        
        **요청 사항**:
        1. **내용 추출**: 이미지면 OCR, 오디오면 핵심 대화 내용을 요약/전사하세요.
        2. **법적 가치 평가**: 이 증거가 민법 제840조(재판상 이혼 사유) 중 어디에 해당하는지 판단하세요.
           (예: 부정행위(1호), 악의적 유기(2호), 부당한 대우(3호) 등)
        3. **신뢰성 검증**: 조작 흔적이나 위조 가능성이 있는지 확인하세요.
        4. **감정/정황 분석**: (오디오의 경우) 화자의 감정 상태나 강압적인 분위기가 감지되나요?
        
        **응답 형식 (JSON)**:
        {{
            "extracted_content": "...",
            "legal_relevance": {{
                "article_840_index": [1, 3], 
                "description": "부정행위 정황 및 폭언 확인됨" 
            }},
            "credibility_score": 0.0~1.0,
            "key_insights": ["..."],
            "summary": "..."
        }}
        """

        # 3. Generate Content
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=[file, prompt],
                config={"response_mime_type": "application/json"}
            )
            result = json.loads(response.text)
            result["file_uri"] = file.uri
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {"error": str(e)}

    def analyze_multiple_divorce_evidence(self, file_paths: List[str], case_context: str) -> Dict[str, Any]:
        """
        여러 증거를 한꺼번에 분석하여 '모순'이나 '연관성'을 찾습니다.
        """
        client = self._get_client()
        uploaded_files = []
        
        for path in file_paths:
            f = client.files.upload(file=path)
            while f.state.name == "PROCESSING":
                time.sleep(1)
                f = client.files.get(name=f.name)
            uploaded_files.append(f)
            
        prompt = f"""
        다음 {len(uploaded_files)}개의 증거 파일들을 종합적으로 분석하세요.
        
        **사건 배경**: {case_context}
        
        **요청 사항**:
        1. 증거들 간의 **타임라인**을 구성하세요.
        2. 서로 **모순**되거나 상충하는 내용이 있는지 찾으세요.
        3. 종합적으로 봤을 때 이혼 소송 승소 확률을 높이는 **결정적 증거**가 무엇인지 지목하세요.
        
        **응답 형식 (JSON)**:
        {{
            "timeline": [
                {{"date": "...", "event": "...", "source_file": "..."}}
            ],
            "consistency_check": "모순 없음/있음 (설명)",
            "critical_evidence": "파일 X가 가장 결정적임",
            "overall_assessment": "..."
        }}
        """
        
        response = client.models.generate_content(
            model=self.model,
            contents=uploaded_files + [prompt],
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)

    def check_evidence_legality(self, evidence_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        증거 수집 방법의 적법성을 판단합니다. (예: 도청, 불법 위치 추적 등)
        """
        client = self._get_client()
        prompt = f"""
        다음 증거 수집 상황에 대해 **통신비밀보호법** 및 **개인정보보호법** 위반 여부를 검토하세요.
        
        **증거 정보**: {json.dumps(evidence_metadata, ensure_ascii=False)}
        
        **체크리스트**:
        1. 당사자 간의 대화 녹음인가? (제3자 녹음은 불법)
        2. 동의 없는 위치 추적 장치 사용인가?
        3. 잠겨있는 타인의 휴대전화를 무단으로 열람했는가?
        
        **응답 형식 (JSON)**:
        {{
            "is_legal": true/false/risk_high,
            "risk_factors": ["제3자 녹음 의심", "비밀번호 해킹 의심"],
            "admissibility": "법적 증거 능력 있음/없음/제한적",
            "advice": "..."
        }}
        """
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)

    def auto_match_precedents_from_image(self, image_path: str) -> Dict[str, Any]:
        """
        이미지(예: 진단서, 각서) 내용을 바탕으로 유사 판례를 자동 검색합니다.
        (Visual RAG Simulation)
        """
        # 1. 이미지 내용 분석
        analysis = self.analyze_single_evidence(image_path, "이미지", ["핵심 키워드 추출"])
        if "error" in analysis: return analysis
        
        keywords = analysis.get("key_insights", [])
        extracted_text = analysis.get("extracted_content", "")
        
        # 2. BigQuery 검색 (Actual Execution)
        # 키워드 중 가장 관련성 높은 1개를 선택하여 검색 (데모용 단순화)
        search_keyword = keywords[0] if keywords else "이혼"
        
        # 간단한 LIKE 검색 쿼리 생성
        project_id = os.getenv("GCP_PROJECT_ID")
        dataset_id = "analytics_150875651" # 하드코딩된 데이터셋 ID (실제 환경에 맞춰 수정 필요)
        table_id = f"{project_id}.{dataset_id}.precedent_cases"
        
        sql = f"""
            SELECT case_name, judgment_date, fault_type, alimony_amount, summary
            FROM `{table_id}`
            WHERE summary LIKE '%{search_keyword}%' OR fault_type LIKE '%{search_keyword}%'
            ORDER BY judgment_date DESC
            LIMIT 3
        """
        
        try:
            query_result = bigquery_execute(sql)
            cases = query_result.get("rows", [])
        except Exception as e:
            logger.error(f"BigQuery search failed: {e}")
            cases = []

        return {
            "image_analysis": analysis,
            "search_keyword": search_keyword,
            "matched_precedents": cases,
            "message": f"'{search_keyword}' 관련 판례 {len(cases)}건을 찾았습니다."
        }

# Wrapper Functions for Tool Definition
analyzer = DivorceEvidenceAnalyzer()

def analyze_divorce_evidence(file_path: str, evidence_type: str, analysis_focus: str) -> Dict[str, Any]:
    """Analyze a single piece of evidence (image, audio, pdf) and return JSON summary only."""
    focus_list = analysis_focus.split(',') if analysis_focus else None
    return analyzer.analyze_single_evidence(file_path, evidence_type, focus_list)

def analyze_multiple_divorce_evidence(file_paths: List[str], case_context: str):
    """Analyze multiple evidence files together for consistency."""
    return analyzer.analyze_multiple_divorce_evidence(file_paths, case_context)

def check_evidence_legality(evidence_description: str):
    """Check if the evidence collection method is legal."""
    return analyzer.check_evidence_legality({"description": evidence_description})

def auto_match_precedents_from_image(image_path: str):
    """Find similar legal precedents based on an image evidence."""
    return analyzer.auto_match_precedents_from_image(image_path)
