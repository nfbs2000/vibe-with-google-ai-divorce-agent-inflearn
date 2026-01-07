import os
import json
import logging
from google import genai
from google.genai import types
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Env
def load_env_file(filepath=".env"):
    try:
        with open(filepath, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        print("❌ .env file not found")

load_env_file()

def test_single_file_indexing():
    # 1. Target File
    # Using the specific file mentioned by user
    target_path = Path("data/court_cases/metadata_json/239243.json")
    
    if not target_path.exists():
        logger.error(f"Target file not found: {target_path}")
        return

    # 2. Load JSON
    logger.info(f"📂 Reading JSON file: {target_path}")
    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except Exception as e:
        logger.error(f"JSON Load Error: {e}")
        return

    # 3. Check Fields
    key_summary = metadata.get('key_summary', '')
    logger.info(f"📝 Key Summary Content (First 50 chars): '{key_summary[:50]}...'")
    if not key_summary:
        logger.error("❌ Key Summary is EMPTY!")
    else:
        logger.info("✅ Key Summary is OK.")

    # 4. Construct Text
    metadata_text = f"Summary: {metadata.get('key_summary', '')} \n Reason: {metadata.get('alimony_reason', '')} \n Fault: {metadata.get('fault_type', 'Unknown')}"
    logger.info(f"📄 Embedding Input Text Length: {len(metadata_text)}")

    # 5. Generate Embedding
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY not found in env")
        return
        
    client = genai.Client(api_key=api_key)
    
    logger.info("🤖 Generating Embedding...")
    try:
        if not metadata_text.strip():
            logger.warning("⚠️ Input text is empty, cannot embed.")
            return

        result = client.models.embed_content(
            model="text-embedding-004",
            contents=metadata_text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                title="Debugging Embedding"
            )
        )
        
        emb_values = result.embeddings[0].values
        logger.info(f"✅ Embedding Success! Dimension: {len(emb_values)}")
        print(f"Sample values: {emb_values[:3]}...")
        
    except Exception as e:
        logger.error(f"🔥 Embedding Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_file_indexing()
