#!/usr/bin/env python3
"""
[실습 예제] Gemini File Search API의 응답 구조(Raw JSON) 뜯어보기

이 스크립트는 "File Search가 실제로 어떻게 근거(Grounding)를 찾아오는가?"를 눈으로 확인하기 위한 도구입니다.

목적:
1. Python SDK가 숨기고 있는 Raw JSON 응답을 직접 확인합니다.
2. 'groundingMetadata' 안에 숨겨진 인용구(Citations)와 청크(Chunks) 정보를 분석합니다.
3. RAG 시스템이 얼마나 정확한 근거를 제시하는지 디버깅합니다.

사용처:
- 챕터 3: File Search vs BigQuery Vector Search 비교 강의 시
- "File Search는 근거를 자동으로 달아준다"는 것을 증명할 때 사용
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

api_key = os.getenv("GOOGLE_API_KEY")
store_name = os.getenv("FILE_SEARCH_STORE_NAME")

if not api_key or not store_name:
    print("❌ 환경 변수 오류: GOOGLE_API_KEY 또는 FILE_SEARCH_STORE_NAME이 설정되지 않았습니다.")
    exit(1)

print("=" * 80)
print("🔍 File Search API 응답 디버깅 (Raw Mode)")
print("=" * 80)
print(f"Store: {store_name}")
print(f"Model: gemini-2.5-flash (File Search 최적화 모델)\n")

# 테스트 쿼리
query = "이미 이혼했는데 과거의 혼인을 무효로 돌릴 수 있어? 대법원 판례가 변경되었다던데 상세히 알려줘"

url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# REST API Payload 구성
# SDK를 쓰지 않고 requests를 쓰는 이유: SDK는 응답 객체를 가공해버려서 Raw JSON 구조를 보기 어렵기 때문입니다.
payload = {
    "contents": [{
        "parts": [{"text": query}]
    }],
    "tools": [{
        "file_search": {
            "file_search_store_names": [store_name]
        }
    }]
}

print(f"📝 질문: {query}\n")
print("⏳ API 호출 중... (Raw HTTP Reqeust)\n")

response = requests.post(
    url,
    headers={"Content-Type": "application/json"},
    params={"key": api_key},
    json=payload,
    timeout=30
)

if response.status_code != 200:
    print(f"❌ API 오류: {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()

print("=" * 80)
print("🔍 전체 API 응답 구조 (JSON)")
print("=" * 80)
# ensure_ascii=False를 해야 한글이 깨지지 않고 보입니다.
print(json.dumps(data, indent=2, ensure_ascii=False))
print()

# 파일로 저장 (나중에 교재 자료로 쓰기 위함)
output_file = Path(__file__).parent / "fixtures" / "api_response_debug.json"
output_file.parent.mkdir(parents=True, exist_ok=True) # 폴더가 없으면 생성

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n💾 전체 응답 파일 저장 완료: {output_file}")

# 핵심 구조 분석
print("\n" + "=" * 80)
print("📊 응답 구조 분석 (Grounding Metadata)")
print("=" * 80)

if "candidates" in data:
    print(f"✅ candidates 존재: {len(data['candidates'])}개")

    for i, candidate in enumerate(data["candidates"]):
        print(f"\n--- Candidate {i+1} ---")
        
        # 답변 텍스트 확인
        if "content" in candidate:
            print(f"  📝 답변 파트(Parts): {len(candidate['content'].get('parts', []))}개")

        # 인용/근거 정보 (가장 중요한 부분)
        if "groundingMetadata" in candidate:
            print(f"  ✅ groundingMetadata 존재! (이것이 RAG의 핵심입니다)")
            gm = candidate["groundingMetadata"]
            
            if "groundingChunks" in gm:
                chunks = gm["groundingChunks"]
                print(f"     📚 찾은 근거 청크(Grounding Chunks): {len(chunks)}개")
                for j, chunk in enumerate(chunks[:3]): # 3개만 미리보기
                    print(f"\n     --- Chunk {j+1} ---")
                    print(json.dumps(chunk, indent=6, ensure_ascii=False))
            else:
                print(f"     ❌ groundingChunks 없음 (문서에서 근거를 못 찾음)")
        else:
            print(f"  ❌ groundingMetadata 없음 (일반 LLM 답변과 동일)")
else:
    print("❌ candidates 없음 (API 응답이 비정상입니다)")
