#!/usr/bin/env python3
import os
import json
import logging
import time
from google import genai
from google.genai import types
from pathlib import Path
from google.cloud import bigquery
from typing import List, Dict, Any

# 로깅 설정 (Logging Setup)
# 시간과 로그 레벨을 포함하여 실행 상태를 명확히 추적합니다.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_env_file(filepath=".env"):
    """
    .env 파일에서 환경 변수를 로드합니다.
    API 키나 프로젝트 설정 등 민감한 정보를 관리하기 위해 사용됩니다.
    """
    try:
        with open(filepath, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass

# 환경 변수 로드
load_env_file()

class BatchIndexer:
    """
    판례 데이터를 BigQuery에 일괄 적재(Batch Indexing)하는 클래스입니다.
    
    주요 기능:
    1. BigQuery 테이블 초기화 (DROP & CREATE)
    2. 로컬 JSON 파일 읽기 및 전처리
    3. Gemini API를 이용한 임베딩 생성 (Rate Limit 고려한 순차 처리 + Sleep)
    4. BigQuery에 데이터 일괄 삽입 (Insert Rows)
    """
    def __init__(self):
        # 환경 변수 또는 기본값으로 프로젝트 설정
        self.project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "pio-test-36cf5"
        self.dataset_id = "divorce_analytics"
        self.table_id = "precedent_cases"
        
        # API 키 확인
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.error("❌ GOOGLE_API_KEY is missing!")
            raise ValueError("GOOGLE_API_KEY is missing")
            
        # 클라이언트 초기화
        self.genai_client = genai.Client(api_key=self.api_key)
        self.bq_client = bigquery.Client(project=self.project_id)
        
    def reset_table(self):
        """
        기존 테이블을 삭제하고 스키마에 맞춰 재생성합니다.
        이는 중복 데이터를 방지하고 항상 깨끗한 상태(Clean Slate)를 유지하기 위함입니다.
        """
        table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        logger.info(f"🗑️  Dropping table {table_ref}...")
        try:
            # 테이블이 없어도 에러가 나지 않도록 not_found_ok=True 설정
            self.bq_client.delete_table(table_ref, not_found_ok=True)
            logger.info("✅ Table dropped.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to drop table: {e}")

        # 스키마 정의: 벡터 컬럼(full_text_embedding)은 REPEATED FLOAT64 모드로 설정
        schema = [
            bigquery.SchemaField("case_id", "STRING"),
            bigquery.SchemaField("case_number", "STRING"),
            bigquery.SchemaField("case_type", "STRING"),
            bigquery.SchemaField("alimony_amount", "INT64"),
            bigquery.SchemaField("alimony_reason", "STRING"),
            bigquery.SchemaField("property_ratio_plaintiff", "FLOAT64"),
            bigquery.SchemaField("marriage_duration_years", "INT64"),
            bigquery.SchemaField("fault_type", "STRING"),
            bigquery.SchemaField("summary", "STRING"),
            bigquery.SchemaField("has_children", "BOOLEAN"),
            bigquery.SchemaField("full_text_embedding", "FLOAT64", mode="REPEATED")
        ]
        
        table = bigquery.Table(table_ref, schema=schema)
        # 클러스터링 필드 설정 (검색 성능 최적화)
        table.clustering_fields = ["fault_type"]
        self.bq_client.create_table(table)
        logger.info(f"✅ Table recreated: {table_ref}")

    def run(self, json_dir: str):
        """
        지정된 디렉토리의 JSON 파일들을 읽어 임베딩을 생성하고 BigQuery에 적재합니다.
        """
        # 1. 테이블 리셋
        self.reset_table()
        
        p = Path(json_dir)
        json_files = sorted(p.glob("**/*.json"))
        
        if not json_files:
            logger.warning("No JSON files found!")
            return

        logger.info(f"📂 Found {len(json_files)} files. Preparing batch...")
        
        # 데이터 준비
        rows_map = {} # 인덱스별 메타데이터 매핑
        texts_to_embed = []
        
        valid_files = [] 
        
        # 2. 파일 읽기 및 텍스트 구성
        for idx, json_file in enumerate(json_files):
            try:
                with open(json_file, 'r') as f:
                    metadata = json.load(f)
                
                # 메타데이터 Validation
                case_id = metadata.get('case_id', json_file.stem)
                
                # 임베딩용 텍스트 구성: 판례의 핵심 정보들을 조합하여 검색 정확도를 높입니다.
                summary = metadata.get('key_summary', '')
                reason = metadata.get('alimony_reason', '')
                fault = metadata.get('fault_type', 'Unknown')
                
                text = f"Case: {metadata.get('filename', 'Unknown')}\nSummary: {summary}\nReason: {reason}\nFault: {fault}"
                
                if not text.strip():
                    logger.warning(f"⚠️ Empty text for {json_file.name}, skipping.")
                    continue
                    
                rows_map[len(texts_to_embed)] = metadata # 인덱스로 저장
                texts_to_embed.append(text)
                valid_files.append(json_file.name)
                
            except Exception as e:
                logger.error(f"❌ Error reading {json_file}: {e}")

        logger.info(f"🤖 Starting sequential embedding for {len(texts_to_embed)} items (with delay)...")
        
        if not texts_to_embed:
            logger.error("No valid texts to embed.")
            return

        rows_to_insert = []
        
        # 3. 임베딩 생성 (순차 처리)
        # 중요: API Rate Limit(RPM)을 피하기 위해 Batch call 대신 Loop + Sleep 방식을 사용합니다.
        for i, text in enumerate(texts_to_embed):
            try:
                # 개별 임베딩 요청
                response = self.genai_client.models.embed_content(
                    model="text-embedding-004",
                    contents=text
                )
                
                # 벡터 추출
                if hasattr(response, 'embeddings') and response.embeddings:
                    vector = response.embeddings[0].values
                else:
                    # Some SDK versions return distinct structure?
                    logger.warning(f"⚠️ Unexpected response structure for {valid_files[i]}")
                    continue

                if not vector:
                     logger.warning(f"⚠️ Empty vector for {valid_files[i]}")
                     continue

                metadata = rows_map[i]
                
                # BigQuery 적재용 Row 생성
                row = {
                    "case_id": metadata.get('case_id', 'Unknown'),
                    "case_number": metadata.get('filename', 'Unknown'),
                    "case_type": metadata.get('case_type', 'Unknown'),
                    "alimony_amount": int(metadata.get('alimony_final_amount', 0)),
                    "alimony_reason": metadata.get('alimony_reason', ''),
                    "property_ratio_plaintiff": float(metadata.get('property_ratio_plaintiff', 0.0)),
                    "marriage_duration_years": int(metadata.get('marriage_duration_years', -1)),
                    "fault_type": metadata.get('fault_type', 'Unknown'),
                    "summary": metadata.get('key_summary', ''),
                    "has_children": metadata.get('has_children', None),
                    "full_text_embedding": vector
                }
                rows_to_insert.append(row)
                logger.info(f"✅ Embedded {i+1}/{len(texts_to_embed)}: {valid_files[i]}")
                
                # [Rate Limit 방어] 2초 대기
                time.sleep(2) 

            except Exception as e:
                logger.error(f"🔥 Failed to embed {valid_files[i]}: {e}")
        
        # 4. BigQuery 일괄 적재
        # 모든 임베딩이 준비되면 한 번에 Insert 합니다.
        if rows_to_insert:
            logger.info(f"🚀 Inserting {len(rows_to_insert)} rows to BigQuery...")
            try:
                errors = self.bq_client.insert_rows_json(f"{self.project_id}.{self.dataset_id}.{self.table_id}", rows_to_insert)
                if not errors:
                    logger.info("🎉 SUCCESS! All data indexed.")
                else:
                    logger.error(f"⚠️ Insert errors: {errors}")
            except Exception as e:
                # Fallback for streaming buffer issues (though we dropped table so should be fine)
                 logger.error(f"⚠️ Insert failed: {e}")

if __name__ == "__main__":
    indexer = BatchIndexer()
    # 메타데이터 JSON 파일이 위치한 경로를 지정하여 실행
    indexer.run("data/court_cases/metadata_json")
