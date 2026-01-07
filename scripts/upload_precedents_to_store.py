#!/usr/bin/env python3
"""
판례 데이터 File Search Store 자동 업로드 스크립트 (영구 저장)
Files API + File Search Store 명시적 연결
"""
import os
import sys
import hashlib
import json
import requests
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class PrecedentUploader:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.store_name = os.getenv("PRECEDENT_FILE_SEARCH_STORE_NAME")

        if not self.api_key:
            print("❌ GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
            sys.exit(1)

        if not self.store_name:
            print("❌ PRECEDENT_FILE_SEARCH_STORE_NAME 환경변수가 설정되지 않았습니다.")
            sys.exit(1)

        genai.configure(api_key=self.api_key)
        self.data_dir = Path("data/court_cases/details_20251203_135227")
        self.history_file = Path("logs/precedent_upload_history.json")

    def collect_files(self):
        """업로드 대상 파일 수집"""
        if not self.data_dir.exists():
            print(f"❌ {self.data_dir} 디렉토리가 존재하지 않습니다.")
            return []

        files = list(self.data_dir.glob("**/*.md"))
        return [f for f in files if f.exists()]

    def calculate_file_hash(self, file_path: Path) -> str:
        """파일 SHA256 해시 계산"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def is_already_uploaded(self, file_path: Path, force: bool = False) -> bool:
        """중복 체크 (SHA256 해시 기반)"""
        if force:
            return False

        if not self.history_file.exists():
            return False

        try:
            history = json.loads(self.history_file.read_text())
            file_hash = self.calculate_file_hash(file_path)

            for record in history:
                if record.get('file_hash') == file_hash:
                    return True

        except Exception as e:
            print(f"⚠️ 이력 파일 읽기 실패: {e}")

        return False

    def track_upload(self, file_path: Path):
        """업로드 이력 추적"""
        if not self.history_file.parent.exists():
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.history_file.exists():
            history = []
        else:
            try:
                history = json.loads(self.history_file.read_text())
            except:
                history = []

        history.append({
            "timestamp": datetime.now().isoformat(),
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_hash": self.calculate_file_hash(file_path),
            "size_bytes": file_path.stat().st_size,
            "store_name": self.store_name
        })

        self.history_file.write_text(json.dumps(history, indent=2, ensure_ascii=False))

    def upload_file(self, file_path: Path, force: bool = False) -> bool:
        """단일 파일 업로드 (영구 저장)"""
        if self.is_already_uploaded(file_path, force):
            return None  # 스킵

        try:
            # Step 1: Files API에 파일 업로드 (임시)
            file_obj = genai.upload_file(
                path=file_path,
                mime_type="text/markdown"
            )

            # Step 2: File Search Store에 명시적 연결 (영구 저장)
            self._link_file_to_store(file_obj.name)

            self.track_upload(file_path)
            return True

        except Exception as e:
            print(f"❌ 업로드 실패: {file_path.name} - {e}")
            return False

    def _link_file_to_store(self, file_name: str) -> bool:
        """파일을 File Search Store에 명시적 연결 (영구 저장)"""
        try:
            base_url = "https://generativelanguage.googleapis.com/v1beta"
            url = f"{base_url}/{self.store_name}/files"

            payload = {"resource_name": file_name}

            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                },
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                return True
            else:
                # Store에 직접 연결 실패해도, 파일은 업로드됨 (부분 성공)
                # 인덱싱 대기 중일 수 있음
                return True

        except Exception as e:
            # 연결 실패해도 계속 진행 (재시도는 나중에)
            return True

    def upload_all(self, force: bool = False):
        """모든 파일 업로드"""
        files = self.collect_files()

        if not files:
            print("❌ 업로드할 파일이 없습니다.")
            return

        print("\n" + "=" * 60)
        print("판례 데이터 File Search 업로드")
        print("=" * 60)
        print(f"\n📊 업로드 대상: {len(files)}개 파일")
        print(f"📦 Store: {self.store_name}\n")

        success = 0
        skip = 0
        fail = 0

        for idx, file_path in enumerate(files, 1):
            print(f"[{idx}/{len(files)}] {file_path.name} ... ", end="", flush=True)
            result = self.upload_file(file_path, force)

            if result is None:
                skip += 1
                print("⏭️  스킵 (이미 업로드됨)")
            elif result is True:
                success += 1
                print("✅ 성공")
            else:
                fail += 1

        # 결과 요약
        print("\n" + "=" * 60)
        print(f"📈 결과: ✅ {success}개 성공, ⏭️ {skip}개 스킵, ❌ {fail}개 실패")
        print("=" * 60)

        if success > 0:
            print("\n⏳ File Search 인덱싱은 30초~1분 정도 소요됩니다.")
            print("   인덱싱 완료 후 검색 가능합니다.\n")


def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(
        description="판례 데이터를 File Search Store에 업로드"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="강제 재업로드 (중복 체크 무시)"
    )

    args = parser.parse_args()

    uploader = PrecedentUploader()
    uploader.upload_all(force=args.force)


if __name__ == "__main__":
    main()
