#!/usr/bin/env python3
"""
[통계 분석 실험] Gemini File Search를 이용한 판례 트렌드 분석

단순 검색을 넘어, LLM에게 "데이터 분석가" 역할을 맡기는 실험입니다.
정해진 키워드(이혼 사유 등)에 대해 File Search를 수행하고, 
검색된 근거 문서(Citation)의 개수를 세어 '빈도수 통계'를 뽑아냅니다.

목적:
1. RAG 시스템이 단순 Q&A뿐만 아니라 거시적인 통계 도출에도 사용될 수 있는지 검증
2. "경제적 갈등이 이혼 사유인 판례가 몇 건인가?" 같은 질문 해결

작동 원리:
- 키워드 리스트 순회 -> File Search 쿼리 -> 응답의 Grounding Metadata 분석 -> 고유한 문서 개수 카운팅
"""
import os
import json
import re
from google import genai
from google.genai import types

def load_env_file(filepath=".env"):
    """환경 변수 로드"""
    try:
        with open(filepath, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass

load_env_file()
API_KEY = os.getenv("GOOGLE_API_KEY")
STORE_NAME_ID = os.getenv("PRECEDENT_FILE_SEARCH_STORE_NAME")

if not API_KEY or not STORE_NAME_ID:
    print("❌ API Key or Store Name missing in .env")
    exit(1)

client = genai.Client(api_key=API_KEY)

# 분석할 키워드 목록 (이혼 소송의 주요 쟁점들)
STAT_KEYWORDS = [
    "부정행위", 
    "폭행 또는 학대", 
    "경제적 갈등", 
    "성격 차이", 
    "가출 또는 유기",
    "자녀 양육"
]

def analyze_precedents():
    results = {}
    total_keywords = len(STAT_KEYWORDS)
    
    print(f"📊 판례 데이터 분석 시작 (대상 키워드: {total_keywords}개)...")
    
    for idx, keyword in enumerate(STAT_KEYWORDS):
        print(f"[{idx+1}/{total_keywords}] '{keyword}' 키워드 분석 중 ... ", end="", flush=True)
        
        try:
            # LLM에게 통계 생성을 요청하는 프롬프트
            # 단순 검색이 아니라 "개수를 세어줘(count logic)"를 요청합니다.
            query = f"판례 저장소 전체에서 '{keyword}'와 관련된 이슈가 핵심 쟁점이거나 이혼 사유로 언급된 판례들을 모두 찾아서 그 개수를 세어줘. 그리고 해당되는 판례 번호들을 리스트로 나열해줘."
            
            response = client.models.generate_content(
                model="gemini-2.5-flash", # 분석 작업에는 빠르고 저렴한 Flash 모델 사용
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[STORE_NAME_ID]
                            )
                        )
                    ]
                )
            )
            
            answer_text = response.text if response.text else ""
            
            # [통계 추출 로직]
            # LLM의 말(Text)을 믿는 대신, 실제로 근거로 제시된 문서(Citation)의 개수를 셉니다.
            # 이것이 더 정확한 'Proxy Metric'이 됩니다.
            
            citation_count = 0
            citations = []
            if response.candidates and response.candidates[0].grounding_metadata:
                meta = response.candidates[0].grounding_metadata
                if meta.grounding_chunks:
                    # URI/Title 기반 중복 제거 (한 문서가 여러 번 인용될 수 있음)
                    seen = set()
                    for chunk in meta.grounding_chunks:
                        if chunk.retrieved_context:
                            title = chunk.retrieved_context.title or "Untitled"
                            if title not in seen:
                                citations.append(title)
                                seen.add(title)
            
            citation_count = len(citations)
            
            results[keyword] = {
                "count_proxy": citation_count, # 근거 문서 수
                "found_cases": citations,      # 발견된 판례 목록
                "summary": answer_text[:200] + "..." # 답변 요약
            }
            print(f"✅ {citation_count}건의 관련 판례 발견.")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results[keyword] = {"error": str(e)}

    # 결과 JSON 저장
    output_path = "data/precedent_stats.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n💾 통계 분석 결과 저장 완료: {output_path}")

if __name__ == "__main__":
    analyze_precedents()
