import os
from google.cloud import bigquery
from google import genai
from google.genai import types

# 1. 환경 변수 로드
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
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
DATASET_ID = os.getenv("BIGQUERY_DATASET")
TABLE_NAME = "precedent_cases" # Based on index_precedents_v2.py
API_KEY = os.getenv("GOOGLE_API_KEY")

if not PROJECT_ID or not DATASET_ID or not API_KEY:
    print("❌ Missing Config: PROJECT_ID, DATASET_ID, or GOOGLE_API_KEY")
    exit(1)

# Initialize Clients
bq_client = bigquery.Client(project=PROJECT_ID)
genai_client = genai.Client(api_key=API_KEY)

def get_embedding(text):
    """Generates embedding for the query using Gemini API."""
    try:
        # Using text-embedding-004 as standard
        result = genai_client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        embedding = result.embeddings[0].values
        print(f"📏 Query Embedding Dimension: {len(embedding)}")
        return embedding
    except Exception as e:
        print(f"❌ Embedding Error: {e}")
        return None

def search_bigquery_vector(query_text, top_k=5):
    """Searches BigQuery using Vector Search (Cosine Similarity)."""
    
    print(f"🔍 Generating embedding for: '{query_text}' ...")
    query_vector = get_embedding(query_text)
    
    if not query_vector:
        return

    print(f"📊 Searching BigQuery Table: {DATASET_ID}.{TABLE_NAME} ...")
    
    # Cosine Distance logic (1 - cosine_similarity for distance, or just cosine_similarity DESC)
    # Using standard SQL for cosine similarity
    sql = f"""
        SELECT 
            case_id,
            case_number,
            summary,
            ml.DISTANCE(
                (SELECT {query_vector}),
                full_text_embedding,
                'COSINE'
            ) as distance
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}`
        WHERE full_text_embedding IS NOT NULL
          AND ARRAY_LENGTH(full_text_embedding) > 0
        ORDER BY distance ASC
        LIMIT {top_k}
    """
    
    try:
        query_job = bq_client.query(sql)
        results = query_job.result()
        
        print(f"\n✅ Top {top_k} Results for '{query_text}':")
        for row in results:
            print(f"\n[Distance: {row.distance:.4f}] {row.case_number} (ID: {row.case_id})")
            print(f"   📝 Summary: {row.summary[:150]}...") # Truncate summary
            
    except Exception as e:
        print(f"❌ BigQuery Search Error: {e}")
        print("   (Note: Ensure 'ml_generate_embedding_cosine_similarity' function is available or use manual dot product if needed)")

if __name__ == "__main__":
    search_bigquery_vector("양육비를 주지 않는 아빠들의 신상을 공개한 배드파더스 운영자가 명예훼손으로 처벌받은 사례")
