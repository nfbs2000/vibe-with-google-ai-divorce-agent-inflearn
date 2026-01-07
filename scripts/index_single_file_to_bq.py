#!/usr/bin/env python3
"""
[유틸리티] 단건 파일 BigQuery 적재 스크립트

이 스크립트는 전체 배치가 아닌, '특정 JSON 파일 하나만' 콕 집어서 BigQuery에 넣고 싶을 때 사용합니다.
주로 디버깅 용도나, 특정 판례만 업데이트해야 할 때 유용합니다.

주의: BigQuery의 Streaming Buffer 제약 때문에 DELETE 후 바로 INSERT 하면 
      데이터가 즉시 조회되지 않을 수 있습니다. (최대 90분 소요)
"""
import os
import json
import logging
from google import genai
from google.genai import types
from pathlib import Path
from google.cloud import bigquery

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_env_file(filepath=".env"):
    try:
        with open(filepath, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass

load_env_file()

def index_single_file():
    # 1. 설정 (Config)
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "pio-test-36cf5"
    dataset_id = "divorce_analytics"
    table_id = "precedent_cases"
    api_key = os.getenv("GOOGLE_API_KEY")
    
    # 2. 클라이언트 초기화
    bq_client = bigquery.Client(project=project_id)
    genai_client = genai.Client(api_key=api_key)

    # 3. 대상 파일 지정 (Target File)
    # 원하는 파일 경로를 직접 지정하세요.
    target_path = Path("data/court_cases/metadata_json/239243.json")
    if not target_path.exists():
        logger.error("❌ File not found.")
        return

    # 4. JSON 로드
    with open(target_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # 5. 임베딩 생성 (Generate Embedding)
    # 배치 스크립트와 동일한 포맷을 사용해야 검색 품질이 유지됩니다.
    metadata_text = f"Case: {metadata.get('filename', 'Unknown')}\nSummary: {metadata.get('key_summary', '')}\nReason: {metadata.get('alimony_reason', '')}\nFault: {metadata.get('fault_type', 'Unknown')}"
    
    logger.info(f"🤖 Generating Embedding for {target_path.name}...")
    try:
        result = genai_client.models.embed_content(
            model="text-embedding-004",
            contents=metadata_text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT", # 문서 저장용 태스크 타입
                title="Single Case Indexing"
            )
        )
        embedding = result.embeddings[0].values
        logger.info(f"✅ Embedding Length: {len(embedding)}")
    except Exception as e:
        logger.error(f"🔥 Embedding Error: {e}")
        return

    # 6. 기존 행 삭제 (선택 사항)
    # BigQuery Streaming Buffer 이슈 때문에 주석 처리해두었습니다.
    # 실시간 수정이 필요하다면 UPDATE/DELETE 대신 새로운 테이블을 만드는 게 더 빠를 수 있습니다.
    case_id = metadata.get('case_id', '239243')
    # query = f"DELETE FROM `{project_id}.{dataset_id}.{table_id}` WHERE case_id = '{case_id}'"
    # bq_client.query(query).result()
    # logger.info(f"🧹 Deleted existing row for case_id: {case_id}")

    # 7. BigQuery 적재 (Insert)
    row = {
        "case_id": case_id,
        "case_number": metadata.get('filename', 'Unknown'),
        "case_type": metadata.get('case_type', 'Unknown'),
        "alimony_amount": int(metadata.get('alimony_final_amount', 0)),
        "alimony_reason": metadata.get('alimony_reason', ''),
        "property_ratio_plaintiff": float(metadata.get('property_ratio_plaintiff', 0.0)),
        "marriage_duration_years": int(metadata.get('marriage_duration_years', -1)),
        "fault_type": metadata.get('fault_type', 'Unknown'),
        "summary": metadata.get('key_summary', ''),
        "has_children": metadata.get('has_children', None),
        "full_text_embedding": embedding
    }

    errors = bq_client.insert_rows_json(f"{project_id}.{dataset_id}.{table_id}", [row])
    if not errors:
        logger.info(f"🎉 Inserted {target_path.name} into BigQuery successfully!")
    else:
        logger.error(f"⚠️ Insert Errors: {errors}")

if __name__ == "__main__":
    index_single_file()
