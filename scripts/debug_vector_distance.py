#!/usr/bin/env python3
import os
import math
from google import genai

# ==================================================================================
# [실습 예제] 벡터 검색(Vector Search)의 한계와 의미적 거리(Semantic Distance) 이해하기
#
# 이 스크립트는 "왜 벡터 검색만으로는 완벽한 법률 검색이 어려운가?"를 보여주는 살아있는 예제입니다.
# 
# 실험 내용:
# 1. Query: "배드파더스(Bad Fathers) 명예훼손 처벌 사례"
# 2. Case A: 실제 배드파더스 판례 (명예훼손 유죄) - 우리가 찾는 정답
# 3. Case B: 마약 사범의 휴대전화 몰수 판례 (전혀 관계 없음)
#
# 기대 결과: Case A가 Query와 더 가까워야 합니다. (Distance가 더 작아야 함)
# 실제 결과: AI 모델은 Case B를 더 가깝다고 판단할 때가 있습니다. (충격!)
#
# 이유: 임베딩 모델은 'Text-Embedding-004' 기준, '명예훼손/양육비'라는 법적 쟁점보다
#      '신상 공개' <-> '사생활/개인정보(휴대전화)' 사이의 문맥적 유사성을 더 크게 평가했기 때문입니다.
#      즉, 인간이 의도한 '법적 주제'와 AI가 해석한 '문맥적 주제'의 미스매치입니다.
#
# 교훈: 이것이 바로 RAG 시스템에서 Hybrid Search(키워드 검색 + 벡터 검색)가 필요한 이유입니다.
# ==================================================================================

# 환경 변수 로드 (.env 파일 처리)
def load_env_file(filepath=".env"):
    try:
        with open(filepath, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except:
        pass

load_env_file()

# Gemini 클라이언트 초기화
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

def get_embedding(text):
    """
    텍스트를 입력받아 768차원 벡터(숫자 리스트)로 변환합니다.
    이 숫자들이 바로 AI가 이해하는 '의미'의 좌표입니다.
    """
    res = client.models.embed_content(model="text-embedding-004", contents=text)
    return res.embeddings[0].values

def cosine_distance(v1, v2):
    """
    두 벡터 사이의 코사인 거리(Cosine Distance)를 계산합니다.
    - 거리 = 0.0: 완전히 동일함
    - 거리 = 1.0: 직교함 (관계 없음)
    - 거리 = 2.0: 정반대임
    
    * 주의: Cosine Similarity(유사도)와 반대 개념입니다. (Distance = 1 - Similarity)
    """
    dot_product = sum(a*b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a*a for a in v1))
    magnitude2 = math.sqrt(sum(b*b for b in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 1.0
    return 1.0 - (dot_product / (magnitude1 * magnitude2))

print("🧪 실험 시작: 벡터 거리 측정 중...")

# 1. 검색어 (Query)
# 사용자가 찾고 싶은 정확한 의도입니다.
query_text = "양육비를 주지 않는 아빠들의 신상을 공개한 배드파더스 운영자가 명예훼손으로 처벌받은 사례"

# 2. Case A (정답 문서 - 배드파더스 판례)
# 텍스트에는 '명예훼손', '양육비', '공익' 등 관련 키워드가 풍부합니다.
text_a = """Case: 239243_2022도699.md
Summary: 양육비를 주지 않는 '나쁜 아빠(Bad Fathers)'들의 사진과 직장 등을 공개해 양육비 지급을 촉구하던 사이트 운영자들이 명예훼손으로 기소된 사건입니다. 운영자들은 '양육비 미지급 해결이라는 공익을 위한 것'이라 주장하며 무죄를 호소했습니다. 하지만 대법원은 '양육비 문제는 공적 관심사지만, 얼굴과 직장명까지 공개한 것은 해결 수단을 넘어선 사적 제재에 가깝고, 피해자들에게 회복할 수 없는 피해를 입혀 비방의 목적이 인정된다'며 유죄를 선고했습니다. 공익과 사적 제재의 경계를 다룬 판례입니다.
Reason: 이 사건은 위자료 청구 소송이 아니라, '배드파더스' 사이트 운영자들에 대한 명예훼손 형사 판결임. 양육비 미지급자 압박 목적(공익)보다 과도한 신상 공개로 인한 인격권 침해(비방 목적)가 더 크다고 보아 유죄가 확정됨.
Fault: 명예훼손"""

text_a_clean = """양육비를 주지 않는 '나쁜 아빠(Bad Fathers)'들의 사진과 직장 등을 공개해 양육비 지급을 촉구하던 사이트 운영자들이 명예훼손으로 기소된 사건입니다. 운영자들은 '양육비 미지급 해결이라는 공익을 위한 것'이라 주장하며 무죄를 호소했습니다. 하지만 대법원은 '양육비 문제는 공적 관심사지만, 얼굴과 직장명까지 공개한 것은 해결 수단을 넘어선 사적 제재에 가깝고, 피해자들에게 회복할 수 없는 피해를 입혀 비방의 목적이 인정된다'며 유죄를 선고했습니다. 공익과 사적 제재의 경계를 다룬 판례입니다.
이 사건은 위자료 청구 소송이 아니라, '배드파더스' 사이트 운영자들에 대한 명예훼손 형사 판결임. 양육비 미지급자 압박 목적(공익)보다 과도한 신상 공개로 인한 인격권 침해(비방 목적)가 더 크다고 보아 유죄가 확정됨.
명예훼손"""

# 3. Case B (오답 문서 - 마약 사범 휴대전화 몰수)
# 텍스트에는 '휴대전화', '사생활', '정보' 등이 나옵니다.
# 사용자는 이걸 원하지 않지만, AI는 쿼리의 '신상 공개'와 이 문서의 '사생활/정보'를 비슷하다고 착각합니다.
text_b = """Case: 239247_xxxx.md
Summary: 마약 투약 혐의로 기소된 피고인의 휴대전화를 몰수할 것인가가 쟁점이 된 사건입니다. 하급심은 피고인이 마약 거래 연락에 휴대전화를 사용했다며 몰수를 선고했습니다. 그러나 대법원은 '휴대전화는 현대인의 모든 사생활과 정보가 담긴 필수품'이라며, 단순히 연락 몇 번에 썼다고 해서 전부 몰수하는 것은 비례의 원칙에 어긋난다'고 보아 원심을 파기했습니다.
Reason: 
Fault: Unknown"""

text_b_clean = """마약 투약 혐의로 기소된 피고인의 휴대전화를 몰수할 것인가가 쟁점이 된 사건입니다. 하급심은 피고인이 마약 거래 연락에 휴대전화를 사용했다며 몰수를 선고했습니다. 그러나 대법원은 '휴대전화는 현대인의 모든 사생활과 정보가 담긴 필수품'이라며, 단순히 연락 몇 번에 썼다고 해서 전부 몰수하는 것은 비례의 원칙에 어긋난다'고 보아 원심을 파기했습니다.
Unknown"""

print(f"🤖 Embedding 생성 중...")
vec_q = get_embedding(query_text)
# Labeled (메타데이터 라벨 있음)
vec_a = get_embedding(text_a)
vec_b = get_embedding(text_b)
# Clean (본문만 있음)
vec_a_clean = get_embedding(text_a_clean)
vec_b_clean = get_embedding(text_b_clean)

# 거리 계산
dist_a = cosine_distance(vec_q, vec_a)
dist_b = cosine_distance(vec_q, vec_b)
dist_a_clean = cosine_distance(vec_q, vec_a_clean)
dist_b_clean = cosine_distance(vec_q, vec_b_clean)

# 결과 출력
print("\n" + "="*50)
print(f"🎯 Query: '{query_text}'")
print("-" * 50)
print(f"1️⃣  Case A (배드파더스/정답) 거리: {dist_a:.4f} (Clean: {dist_a_clean:.4f})")
print(f"2️⃣  Case B (마약사건/오답)   거리: {dist_b:.4f} (Clean: {dist_b_clean:.4f})")
print("="*50)

# 최종 판정
print("\n[판정 결과]")
if dist_a < dist_b:
    print("✅ 성공: AI가 정답(배드파더스)을 더 가깝다고 판단했습니다.")
else:
    print("❌ 실패: AI가 오답(마약사건)을 더 가깝다고 판단했습니다.")
    print("   -> 이유: '신상공개'와 '개인정보/사생활' 사이의 의미적 유사성이")
    print("            '명예훼손' 법리보다 더 강하게 작용했기 때문일 수 있습니다.")
    print("   -> 해결책: 키워드 검색(BM25)을 섞거나, Reranking 모델을 사용해야 합니다.")
