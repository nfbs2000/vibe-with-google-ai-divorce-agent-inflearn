# ADK Backend - 메인 백엔드 서비스

Google Agent Development Kit(ADK)를 기반으로 한국어 NLP와 BigQuery 분석을 처리하는 메인 백엔드 서비스입니다.  
이 프로젝트는 ADK 런타임과 툴 체계를 활용하여 한국어 자연어 쿼리를 BigQuery SQL로 변환하고 실행하는 전문 에이전트를 제공합니다.

## 🚀 주요 기능

- **한국어 NLP 처리**: Gemini 1.5 Flash 모델을 활용한 자연어 쿼리 이해
- **BigQuery 전문 에이전트**: ADK 기반 안전하고 효율적인 SQL 생성 및 실행
- **템플릿 기반 쿼리**: 사전 정의된 SQL 템플릿을 활용한 보안 강화
- **실시간 스트리밍**: SSE 기반 실시간 쿼리 결과 스트리밍
- **RESTful API**: FastAPI 기반 완전한 백엔드 API 서비스

## 주요 구성

- `src/adk_backend/app.py` – FastAPI 엔드포인트와 ADK 러너 초기화
- `src/adk_backend/agents/` – ADK `Agent` 정의
- `src/adk_backend/tools/` – ADK `@tool` 기반 커스텀 BigQuery 툴
- `src/adk_backend/workflows/` – ADK `Workflow`/`Runner` 조합

## 🚀 실행 방법

### 개발 환경 설정

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install --upgrade pip
pip install -e .

# 3. 서버 실행 (포트 8004)
python -m uvicorn adk_backend.app:app --reload --host 0.0.0.0 --port 8004
```

### 프론트엔드와 함께 실행

```bash
# 터미널 1: ADK 백엔드 서버
cd adk-backend
source venv/bin/activate
python -m uvicorn adk_backend.app:app --reload --host 0.0.0.0 --port 8004

# 터미널 2: 프론트엔드 서버
cd ../frontend
npm run dev
```

## 환경 변수

`.env` 또는 시스템 환경 변수에 다음 값을 설정하세요.

- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `BIGQUERY_DEFAULT_DATASET`

## 📚 API 엔드포인트

### Chat API
- `POST /api/chat/query` - 한국어 자연어 쿼리 처리
- `GET /api/chat/examples` - 예시 쿼리 목록

### Data API  
- `GET /api/data/sources` - 사용 가능한 데이터 소스 목록
- `GET /api/data/tables` - BigQuery 테이블 정보
- `GET /api/data/tables/{table_name}/schema` - 테이블 스키마 조회

### ADK API
- `POST /api/run` - ADK 에이전트 실행
- `POST /api/live/run` - 실시간 스트리밍 실행
- `GET /api/live/events` - SSE 이벤트 스트림
- `GET /api/templates` - BigQuery 템플릿 목록
- `POST /api/templates/render` - 템플릿 렌더링

### System API
- `GET /health` - 서비스 상태 확인

## 🔧 개발 및 확장

- 새로운 BigQuery 템플릿 추가: `src/adk_backend/tools/bigquery.py`
- 에이전트 설정 수정: `src/adk_backend/agents/bigquery_agent.py`
- API 엔드포인트 추가: `src/adk_backend/api/`
