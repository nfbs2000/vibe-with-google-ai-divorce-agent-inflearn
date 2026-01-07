import React, { useState } from 'react';
import { AlertCircle, FileText, Scale, Sparkles, TrendingUp, CheckCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { DivorceEvidenceUploader } from './DivorceEvidenceUploader';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Badge } from './ui/badge';

interface AnalysisResult {
  response: string;
  ocr_text?: string;
  patterns?: Array<{
    type: string;
    description: string;
    severity: 'high' | 'medium' | 'low';
  }>;
  legal_assessment?: {
    liability_type: string;
    confidence: number;
    reasoning: string;
  };
  recommendations?: string[];
  precedents?: Array<{
    case_id: string;
    case_name: string;
    similarity_score: number;
    summary: string;
  }>;
  timeline?: Array<{
    date: string;
    event: string;
    evidence_type: string;
  }>;
  rag_references?: Array<{
    case_number: string;
    summary: string;
    link: string;
  }>;
}

export const DivorceEvidenceAnalysisPanel: React.FC = () => {
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [caseDescription, setCaseDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFilesUploaded = (filePaths: string[]) => {
    setUploadedFiles(prev => [...prev, ...filePaths]);
  };

  const handleAnalyze = async () => {
    const startTime = performance.now();

    if (uploadedFiles.length === 0) {
      setError('최소 1개 이상의 증거 파일을 업로드해주세요.');
      return;
    }

    if (!caseDescription.trim()) {
      setError('사건 개요를 입력해주세요.');
      return;
    }

    console.log('=' .repeat(80));
    console.log('🔍 [이혼증거분석] 분석 시작');
    console.log(`📦 파일 개수: ${uploadedFiles.length}개`);
    console.log(`📋 케이스 설명 길이: ${caseDescription.length}자`);
    console.log('파일 목록:');
    uploadedFiles.forEach((path, idx) => {
      console.log(`  ${idx + 1}. ${path}`);
    });

    setIsAnalyzing(true);
    setError(null);

    try {
      const requestBody = {
        query: `이혼 증거 분석을 요청합니다.

사건 개요: ${caseDescription}

업로드된 증거 파일 (${uploadedFiles.length}개):
${uploadedFiles.map((path, idx) => `${idx + 1}. ${path}`).join('\n')}

다음 항목을 분석해주세요:
1. 각 증거 파일의 OCR 및 내용 분석
2. 발견된 패턴 및 상관관계
3. 유책배우자 판단 (민법 제840조 기준)
4. 유사 판례 검색 및 매칭 (RAG)
5. 법적 조언 및 권장사항
6. 증거의 시간순 타임라인

**중요 요청사항**:
- 판례 검색 결과(RAG)가 있다면, 답변의 마지막에 '## 📚 참조 판례 (RAG Sources)' 섹션을 별도로 만들어주세요.
- 각 판례의 **판례번호**, **요약**, **출처 링크**를 명시해주세요.
- 분석 내용 중 실제 판례에 기반한 부분은 인용 표시나 출처를 언급하여, AI의 주관적 판단과 실제 법적 근거를 명확히 구분해주세요.`,
        user_id: 'demo-user',
        session_id: 'divorce-analysis',
        agent_type: 'conversational',
        files: uploadedFiles,
      };

      console.log('📤 API 요청 전송 중...');
      console.log(`🎯 엔드포인트: /api/chat/query`);

      const response = await fetch('/api/chat/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`분석 요청 실패: ${response.statusText}`);
      }

      console.log('📥 서버 응답 수신 중...');
      const data = await response.json();

      const analysisTime = ((performance.now() - startTime) / 1000).toFixed(2);
      console.log(`✅ 분석 완료!`);
      console.log(`⏱️ 총 소요시간: ${analysisTime}초`);
      console.log(`📝 응답 길이: ${data.response?.length || 0}자`);

      // Parse the response to extract structured data
      // This is a simplified version - in production, the backend should return structured data
      const result = {
        response: data.response,
        // These would be parsed from the actual response or returned by the backend
        patterns: [],
        legal_assessment: undefined,
        recommendations: [],
        precedents: [],
        timeline: [],
        rag_references: data.rag_references || [],
      };

      console.log('📊 분석 결과:');
      console.log(`  - 응답: ${result.response ? '✓' : '✗'}`);
      console.log('=' .repeat(80));

      setAnalysisResult(result);
    } catch (err) {
      const analysisTime = ((performance.now() - startTime) / 1000).toFixed(2);
      const errorMessage = err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.';

      console.error('=' .repeat(80));
      console.error('❌ [이혼증거분석] 분석 실패!');
      console.error(`📦 파일 개수: ${uploadedFiles.length}개`);
      console.error(`🚨 오류 메시지: ${errorMessage}`);
      console.error(`⏱️ 실패까지 소요시간: ${analysisTime}초`);
      console.error('=' .repeat(80));

      setError(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const renderAnalysisResults = () => {
    if (!analysisResult) return null;

    return (
      <div className="space-y-6 mt-6">
        {/* AI 분석 결과 */}
        <Card className="p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Sparkles className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold">AI 분석 결과</h3>
          </div>
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown className="text-gray-700">
              {analysisResult.response}
            </ReactMarkdown>
          </div>
        </Card>

        {/* OCR 텍스트 */}
        {analysisResult.ocr_text && (
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              <FileText className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-semibold">추출된 텍스트 (OCR)</h3>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg text-sm font-mono">
              {analysisResult.ocr_text}
            </div>
          </Card>
        )}

        {/* 패턴 분석 */}
        {analysisResult.patterns && analysisResult.patterns.length > 0 && (
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              <TrendingUp className="w-5 h-5 text-emerald-600" />
              <h3 className="text-lg font-semibold">발견된 패턴</h3>
            </div>
            <div className="space-y-3">
              {analysisResult.patterns.map((pattern, idx) => (
                <div
                  key={idx}
                  className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg"
                >
                  <Badge
                    variant={
                      pattern.severity === 'high'
                        ? 'destructive'
                        : pattern.severity === 'medium'
                        ? 'default'
                        : 'outline'
                    }
                  >
                    {pattern.severity}
                  </Badge>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{pattern.type}</p>
                    <p className="text-xs text-gray-600 mt-1">
                      {pattern.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* 법적 평가 */}
        {analysisResult.legal_assessment && (
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              <Scale className="w-5 h-5 text-amber-600" />
              <h3 className="text-lg font-semibold">법적 평가</h3>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">유책 유형</span>
                <Badge variant="default">
                  {analysisResult.legal_assessment.liability_type}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">신뢰도</span>
                <span className="text-sm font-semibold">
                  {(analysisResult.legal_assessment.confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div className="pt-3 border-t border-gray-200">
                <p className="text-sm text-gray-700">
                  {analysisResult.legal_assessment.reasoning}
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* 권장사항 */}
        {analysisResult.recommendations &&
          analysisResult.recommendations.length > 0 && (
            <Card className="p-6">
              <div className="flex items-center space-x-2 mb-4">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <h3 className="text-lg font-semibold">권장사항</h3>
              </div>
              <ul className="space-y-2">
                {analysisResult.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <span className="text-green-600 mt-1">✓</span>
                    <span className="text-sm text-gray-700">{rec}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}

        {/* 유사 판례 */}
        {analysisResult.precedents && analysisResult.precedents.length > 0 && (
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              <FileText className="w-5 h-5 text-indigo-600" />
              <h3 className="text-lg font-semibold">유사 판례</h3>
            </div>
            <div className="space-y-4">
              {analysisResult.precedents.map((precedent, idx) => (
                <div
                  key={idx}
                  className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-medium text-sm">{precedent.case_name}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {precedent.case_id}
                      </p>
                    </div>
                    <Badge variant="outline">
                      유사도 {(precedent.similarity_score * 100).toFixed(0)}%
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-700 mt-2">
                    {precedent.summary}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* 증거 타임라인 */}
        {analysisResult.timeline && analysisResult.timeline.length > 0 && (
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-semibold">증거 타임라인</h3>
            </div>
            <div className="space-y-3">
              {analysisResult.timeline.map((item, idx) => (
                <div key={idx} className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-24 text-sm text-gray-600">
                    {item.date}
                  </div>
                  <div className="flex-1 border-l-2 border-gray-300 pl-4 pb-4">
                    <Badge variant="outline" className="mb-1">
                      {item.evidence_type}
                    </Badge>
                    <p className="text-sm text-gray-700">{item.event}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* RAG 참조 판례 (Clickable) */}
        {analysisResult.rag_references && analysisResult.rag_references.length > 0 && (
          <Card className="p-6">
            <div className="flex items-center space-x-2 mb-4">
              <FileText className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-semibold">📚 참조 판례 (RAG Sources)</h3>
            </div>
            <div className="space-y-4">
              {analysisResult.rag_references.map((ref, idx) => (
                <div
                  key={idx}
                  className="p-4 border border-gray-200 rounded-lg hover:bg-blue-50 transition-colors cursor-pointer"
                  onClick={() => window.open(ref.link, '_blank')}
                >
                  <div className="flex items-start justify-between mb-2">
                    <p className="font-bold text-sm text-blue-800 hover:underline">
                      {ref.case_number}
                    </p>
                    <Badge variant="outline" className="text-xs">
                      Source
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-700">{ref.summary}</p>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* 법적 고지사항 */}
        <Card className="p-6 bg-amber-50 border-amber-200">
          <div className="flex">
            <AlertCircle className="w-5 h-5 text-amber-600 mr-3 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-900">
              <p className="font-semibold mb-2">⚖️ 법적 고지사항</p>
              <ul className="list-disc list-inside space-y-1 text-xs">
                <li>
                  본 AI 분석은 참고용이며 법적 효력이 없습니다. 실제 법적 조치를
                  위해서는 반드시 변호사와 상담하세요.
                </li>
                <li>
                  판례 매칭은 키워드 및 패턴 기반으로 이루어지며, 실제 사건과
                  차이가 있을 수 있습니다.
                </li>
                <li>
                  증거의 법적 효력은 법원에서 최종 판단하며, AI 분석 결과와
                  다를 수 있습니다.
                </li>
                <li>
                  중요한 결정을 내리기 전에 반드시 법률 전문가의 조언을
                  구하시기 바랍니다.
                </li>
              </ul>
            </div>
          </div>
        </Card>
      </div>
    );
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* 헤더 */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          이혼 증거 분석 시스템
        </h1>
        <p className="text-gray-600">
          AI 기반 멀티모달 증거 분석 및 판례 검색 서비스
        </p>
      </div>

      {/* 파일 업로드 섹션 */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">1. 증거 파일 업로드</h2>
        <DivorceEvidenceUploader onFilesUploaded={handleFilesUploaded} />

        {uploadedFiles.length > 0 && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm font-medium text-green-900">
              ✓ 총 {uploadedFiles.length}개 파일이 업로드되었습니다.
            </p>
          </div>
        )}
      </Card>

      {/* 사건 개요 입력 */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">2. 사건 개요 입력</h2>
        <textarea
          value={caseDescription}
          onChange={e => setCaseDescription(e.target.value)}
          placeholder="이혼 사건의 전반적인 상황을 설명해주세요. 예:&#10;- 결혼 기간 및 자녀 유무&#10;- 이혼 사유 (부정행위, 악의의 유기, 학대 등)&#10;- 주요 쟁점 사항&#10;- 원하시는 분석 초점"
          className="w-full p-4 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          rows={8}
        />
        <p className="text-xs text-gray-500 mt-2">
          자세한 정보를 제공할수록 더 정확한 분석이 가능합니다.
        </p>
      </Card>

      {/* 에러 메시지 */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-sm text-red-900">{error}</p>
          </div>
        </div>
      )}

      {/* 분석 시작 버튼 */}
      <div className="flex justify-center">
        <Button
          onClick={handleAnalyze}
          disabled={isAnalyzing || uploadedFiles.length === 0}
          size="lg"
          className="px-8 py-3"
        >
          {isAnalyzing ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
              분석 중...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5 mr-2" />
              AI 증거 분석 시작
            </>
          )}
        </Button>
      </div>

      {/* 분석 결과 */}
      {renderAnalysisResults()}
    </div>
  );
};
