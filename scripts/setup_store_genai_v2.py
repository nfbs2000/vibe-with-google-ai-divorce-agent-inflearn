#!/usr/bin/env python3
"""
[설치 스크립트] File Search Store 생성 및 데이터 업로드

이 스크립트는 'File Search' 실습을 위한 "서버 구축 스크립트"라고 보시면 됩니다.
BigQuery 테이블을 만드는 것처럼, Gemini 쪽에 '판례 저장소(Store)'를 만들고 파일을 업로드합니다.

주요 기능:
1. 저장소(Store) 생성: 'Precedent_Store_Smart_V3'라는 이름의 저장소를 만듭니다.
2. 스마트 업로드: 로컬 파일이 이미 클라우드에 있다면 재사용(Skip)하고, 없는 것만 업로드합니다.
3. 환경 변수 등록: 생성된 저장소 ID를 .env 파일에 자동으로 저장합니다. -> 다른 스크립트들이 갖다 쓸 수 있게 함.

사용 시점:
- 프로젝트를 처음 세팅할 때 1회 실행
- 데이터가 추가되어 저장소를 갱신하고 싶을 때 실행
"""
import os
import time
from pathlib import Path
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
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("❌ GOOGLE_API_KEY Missing")
    exit(1)

client = genai.Client(api_key=API_KEY)

def setup_store_smart_v2():
    # 데이터 경로 설정 (Markdown 파일들이 있는 곳)
    data_dir = "data/court_cases/details_20251203_135227"
    local_files = list(Path(data_dir).glob("*.md"))
    
    print(f"📊 로컬 판례 파일 발견: {len(local_files)}개")
    
    # 2. 클라우드에 이미 올라가 있는 파일 확인 (재사용을 위해)
    print("🔍 클라우드 파일함 조회 중 (중복 업로드 방지)...")
    existing_cloud_files = {} # displayName -> file_resource_name
    
    try:
        # Paging 처리가 필요할 수 있으나, 여기선 간단히 100개 조회
        for f in client.files.list(config={'page_size': 100}): 
            if f.display_name:
                existing_cloud_files[f.display_name] = f.name
    except Exception as e:
        print(f"⚠️ 파일 목록 조회 실패 (무시하고 진행): {e}")

    print(f"☁️ 클라우드 캐시된 파일: {len(existing_cloud_files)}개")

    # 3. 업로드할 파일 선별 (없는 파일만)
    files_to_index = []
    
    for local_path in local_files:
        dname = local_path.name
        if dname in existing_cloud_files:
            # 이미 있으면 ID만 가져다 씀 (돈과 시간 절약)
            files_to_index.append(existing_cloud_files[dname])
        else:
            # 없으면 업로드
            print(f"🚀 신규 업로드: {dname}")
            try:
                up_f = client.files.upload(file=local_path, config={'display_name': dname})
                existing_cloud_files[dname] = up_f.name # 캐시 갱신
                files_to_index.append(up_f.name)
            except Exception as e:
                print(f"❌ 업로드 실패 {dname}: {e}")

    if not files_to_index:
        print("❌ 업로드할 파일이 없습니다.")
        return

    # 4. 저장소(Store) 생성 및 파일 연결
    store_name_display = "Precedent_Store_Smart_V3"
    print(f"\n🔨 저장소 생성 중: '{store_name_display}' (대상 파일 {len(files_to_index)}개)...")
    
    try:
        # Store 생성
        store = client.file_search_stores.create(
            config={'display_name': store_name_display}
        )
        print(f"✅ 저장소 생성 완료: {store.name}")
        
        print("🔗 파일들을 저장소에 연결(Indexing) 중...")
        count = 0
        for file_res_name in files_to_index:
             try:
                 # 이미 업로드된 파일을 저장소에 등록(Import)
                 client.file_search_stores.import_file(
                     file_search_store_name=store.name,
                     file_name=file_res_name
                 )
                 count += 1
                 if count % 10 == 0:
                     print(f"   연결 진행률 {count}/{len(files_to_index)}")
             except Exception as e:
                 print(f"❌ 연결 오류 {file_res_name}: {e}")

        print(f"✅ 총 {count}개 파일이 저장소에 등록되었습니다.")
        
        # .env 파일 업데이트 (중요: 다른 스크립트들이 이 ID를 쓰기 때문)
        update_env_file(store.name)
        
    except Exception as e:
        print(f"❌ 저장소 생성 실패: {e}")

def update_env_file(new_store_name):
    print(f"\n📝 .env 파일 업데이트 -> PRECEDENT_FILE_SEARCH_STORE_NAME={new_store_name}")
    try:
        with open(".env", "r") as f:
            lines = f.readlines()
        with open(".env", "w") as f:
            updated = False
            for line in lines:
                if line.startswith("PRECEDENT_FILE_SEARCH_STORE_NAME="):
                    f.write(f"PRECEDENT_FILE_SEARCH_STORE_NAME={new_store_name}\n")
                    updated = True
                else:
                    f.write(line)
            if not updated:
                f.write(f"\nPRECEDENT_FILE_SEARCH_STORE_NAME={new_store_name}\n")
    except: pass

if __name__ == "__main__":
    setup_store_smart_v2()
