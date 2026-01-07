
import os
from google.cloud import aiplatform
from google.auth import default

def list_models():
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "pio-test-36cf5")
    location = "us-central1"
    
    print(f"Checking models in project: {project_id}, location: {location}")
    
    aiplatform.init(project=project_id, location=location)
    
    try:
        # Model Garden의 모델을 조회하는 것은 복잡할 수 있으므로,
        # Generative AI 모델을 나열하는 방법을 시도합니다.
        # 하지만 SDK에서 직접적인 list_models가 없을 수 있어,
        # 에러 메시지에서 제안한 대로 ListModels API를 호출하는 방식을 흉내내거나
        # google.generativeai 라이브러리를 사용해봅니다.
        
        import google.generativeai as genai
        
        # API Key가 필요할 수 있음. .env에서 로드 필요.
        # 하지만 Vertex AI를 쓴다면 google-cloud-aiplatform을 써야 함.
        
        from vertexai.preview.generative_models import GenerativeModel
        import vertexai
        
        vertexai.init(project=project_id, location=location)
        
        print("Attempting to list models via Vertex AI SDK...")
        # Vertex AI SDK does not have a simple list_models for foundation models easily accessible via code 
        # without using the Model Garden API which is complex.
        
        # Instead, let's try to instantiate the specific model and see if it fails, 
        # or try a known working model to confirm connectivity.
        
        target_model = "gemini-3-pro-preview-11-2025"
        print(f"Testing instantiation of model: {target_model}")
        
        try:
            model = GenerativeModel(target_model)
            print(f"Successfully instantiated {target_model} object (client-side).")
            # Note: This doesn't guarantee it exists on server until we make a call.
        except Exception as e:
            print(f"Failed to instantiate model object: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    list_models()
