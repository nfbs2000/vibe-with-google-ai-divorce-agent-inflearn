import os
from google import genai
from google.genai import types

# 1. Load Environment Variables
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
API_KEY = os.getenv("GOOGLE_API_KEY")
STORE_NAME_ID = os.getenv("PRECEDENT_FILE_SEARCH_STORE_NAME")

if not API_KEY or not STORE_NAME_ID:
    print("❌ API Key or Store Name missing in .env")
    exit(1)

client = genai.Client(api_key=API_KEY)

def search_precedents(query):
    # Official Doc Model: gemini-2.5-flash
    model_id = "gemini-2.5-flash"
    
    print(f"🔍 Searching with {model_id} for: '{query}' ...")
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=f"판례 저장소에서 '{query}'와 관련된 사례를 찾아서, 판례 번호와 판결 요지를 요약해줘.",
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
        
        print("\n--- 📝 Answer ---")
        if response.text:
            print(response.text)
        else:
            print("(No text response)")
        
        # Citations
        if response.candidates and response.candidates[0].grounding_metadata:
             print("\n--- 📚 Citations ---")
             meta = response.candidates[0].grounding_metadata
             if meta.grounding_chunks:
                 for i, chunk in enumerate(meta.grounding_chunks):
                     if chunk.retrieved_context:
                         title = chunk.retrieved_context.title or "Untitled"
                         uri = chunk.retrieved_context.uri or "No URI"
                         print(f"[{i+1}] {title} ({uri})")

    except Exception as e:
        print(f"❌ Search Error: {e}")

if __name__ == "__main__":
    search_precedents("판례 본문에 '유책'이라는 단어가 실제로 포함되어 있는지 확인하고, 만약 있다면 그 단어가 들어간 문장을 그대로 발췌해서 보여줘. 그리고 해당 판례 번호도 알려줘.")
