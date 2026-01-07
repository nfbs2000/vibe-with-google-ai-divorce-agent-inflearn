#!/usr/bin/env python3
"""
검증 결과를 ANSWER_RESULTS.md로 생성

verification_results.json을 읽어서 마크다운 문서 생성
"""
import json
from pathlib import Path

# 최신 검증 결과 로드
results_file = Path(__file__).parent / "fixtures" / "verification_results.json"
with open(results_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# ANSWER_RESULTS.md 생성
output = []
output.append('# File Search API 답변 결과 전체 기록 (Citations 포함)')
output.append('')
output.append(f"**검증 실행 시각**: {data['timestamp']}")
output.append(f"**모델**: {data['model']}")
output.append(f"**File Search Store**: {data['store_name']}")
output.append(f"**총 테스트 케이스**: {data['total_cases']}개")
output.append(f"**성공률**: {data['passed_cases']/data['total_cases']*100:.1f}%")
output.append('')
output.append('---')
output.append('')

for idx, test in enumerate(data['test_results'], 1):
    output.append(f"## Test Case {idx}: {test['test_id']}")
    output.append('')
    output.append('### 질문')
    output.append('```')
    output.append(test['question'])
    output.append('```')
    output.append('')
    output.append('### File Search API 답변 (전체)')
    output.append('```')
    output.append(test['answer'])
    output.append('```')
    output.append('')
    output.append('### 예상 키워드')
    for kw in test['expected_keywords']:
        output.append(f'- {kw}')
    output.append('')
    output.append('### 찾은 키워드')
    if test['found_keywords']:
        for kw in test['found_keywords']:
            output.append(f'- {kw}')
    else:
        output.append('(없음)')
    output.append('')
    output.append(f"### Citations ({len(test['citations'])}개)")
    for i, citation in enumerate(test['citations'], 1):
        source = citation.get('source', 'Unknown')
        content = citation.get('content', '')
        content_preview = (content[:200] + '...') if len(content) > 200 else content

        output.append(f'{i}. **{source}**')
        if content_preview:
            output.append('   ```')
            output.append(f'   {content_preview}')
            output.append('   ```')
        output.append('')
    output.append('---')
    output.append('')

output.append('## 검증 요약')
output.append('')
output.append(f"- **총 테스트 케이스**: {data['total_cases']}개")
output.append(f"- **통과**: {data['passed_cases']}개")
output.append(f"- **실패**: {data['failed_cases']}개")
output.append(f"- **성공률**: {data['passed_cases']/data['total_cases']*100:.1f}%")
output.append('')
output.append('## ADK 공식 문서 업로드 완료')
output.append('')
output.append('File Search Store에 업로드된 ADK 공식 문서:')
output.append('- Multi-Agent Systems (agents/multi-agents.md)')
output.append('- LLM Agents (agents/llm-agents.md)')
output.append('- Workflow Agents (agents/workflow-agents.md)')
output.append('- Sequential Agents (agents/workflow-agents/sequential-agents.md)')
output.append('- Parallel Agents (agents/workflow-agents/parallel-agents.md)')
output.append('- Loop Agents (agents/workflow-agents/loop-agents.md)')
output.append('- Agents Overview (agents/)')
output.append('- Models & Authentication (agents/models.md)')
output.append('- Agent Config (agents/config.md)')
output.append('')
output.append('---')
output.append('')
output.append('**참고**: 위 답변은 File Search API가 반환한 전체 내용과 Citations를 수정 없이 그대로 기록한 것입니다.')
output.append('')

# 파일 저장
answer_file = Path(__file__).parent / "fixtures" / "ANSWER_RESULTS.md"
answer_file.write_text('\n'.join(output), encoding='utf-8')

print(f'✅ ANSWER_RESULTS.md 업데이트 완료: {answer_file}')
print(f'   - 총 {len(data["test_results"])}개 테스트 케이스')
print(f'   - 성공률: {data["passed_cases"]}/{data["total_cases"]} ({data["passed_cases"]/data["total_cases"]*100:.1f}%)')
