/**
 * UnifiedChatInterface - 4-Layer 통합 아키텍처 채팅 인터페이스
 *
 * ExecutionModeSelector, DomainClassificationDisplay, UnifiedProcessFlow를 통합한 채팅 UI
 */
import React, { useState } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { apiService } from '../services/api'
import {
  ExecutionMode,
  UnifiedQueryResponse,
  DomainClassification,
  ProcessStep,
  StepStatus,
  Domain
} from '../types'
import ExecutionModeSelector from './ExecutionModeSelector'
import DomainClassificationDisplay from './DomainClassificationDisplay'
import UnifiedProcessFlow from './UnifiedProcessFlow'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  response?: UnifiedQueryResponse
}

export const UnifiedChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedMode, setSelectedMode] = useState<ExecutionMode>('auto')

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await apiService.processUnifiedQuery({
        message: input,
        execution_mode: selectedMode,
        user_id: 'demo-user',
        session_id: 'demo-session'
      })

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        response
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Query failed:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `오류가 발생했습니다: ${error instanceof Error ? error.message : '알 수 없는 오류'}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // ProcessStep 변환 함수
  const convertToProcessSteps = (response: UnifiedQueryResponse): ProcessStep[] => {
    const steps: ProcessStep[] = []
    const trace = response.process_trace

    // Layer 1: Domain Router
    steps.push({
      layer: 1,
      name: 'Domain Router',
      status: 'completed',
      data: {
        domain: trace.domain_classification.domain,
        confidence: trace.domain_classification.confidence
      },
      details: [
        `도메인: ${trace.domain_classification.domain}`,
        `신뢰도: ${(trace.domain_classification.confidence * 100).toFixed(0)}%`,
        `매칭 키워드: ${trace.domain_classification.matched_keywords.join(', ')}`
      ]
    })

    // Layer 2: Domain Context
    steps.push({
      layer: 2,
      name: 'Domain Context',
      status: 'completed',
      data: {
        tables: trace.domain_context.tables,
        metrics: trace.domain_context.metrics
      },
      details: [
        `사용 테이블: ${trace.domain_context.tables.length}개`,
        `핵심 메트릭: ${trace.domain_context.metrics.length}개`
      ]
    })

    // Layer 3: Execution Mode
    steps.push({
      layer: 3,
      name: 'Execution Mode',
      status: 'completed',
      data: {
        mode: trace.execution_mode.mode,
        tools: trace.execution_mode.tools
      },
      details: [
        `실행 방식: ${trace.execution_mode.mode}`,
        `사용 도구: ${trace.execution_mode.tools.join(', ')}`,
        trace.execution_mode.reasoning
      ]
    })

    // Layer 4: Agent Execution
    steps.push({
      layer: 4,
      name: 'Agent Execution',
      status: 'completed',
      data: {
        agent: trace.agent_execution.agent_name,
        model: trace.agent_execution.model
      },
      details: [
        `에이전트: ${trace.agent_execution.agent_name}`,
        `모델: ${trace.agent_execution.model}`,
        `도구 호출 횟수: ${trace.agent_execution.tool_calls.length}회`
      ]
    })

    return steps
  }

  // DomainClassification 변환 함수
  const convertToDomainClassification = (response: UnifiedQueryResponse): DomainClassification => {
    return {
      domain: response.domain as Domain,
      confidence: response.domain_confidence,
      matched_keywords: response.process_trace.domain_classification.matched_keywords,
      suggested_tables: response.process_trace.domain_classification.suggested_tables,
      reasoning: response.domain_reasoning
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">4-Layer 통합 분석 시스템</h1>
              <p className="text-sm text-gray-600 mt-1">
                Layer 1: 도메인 라우터 → Layer 2: 도메인 컨텍스트 → Layer 3: 실행 모드 선택 → Layer 4: 에이전트 실행
              </p>
            </div>
            <ExecutionModeSelector
              selectedMode={selectedMode}
              onModeChange={setSelectedMode}
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {/* Main Chat Area */}
        <div className="h-full flex flex-col max-w-7xl mx-auto px-6">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto py-4 space-y-6">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`w-full ${message.role === 'user' ? 'max-w-3xl ml-auto bg-blue-500 text-white' : 'bg-white'} rounded-lg p-6 shadow`}>
                  <div className="text-sm font-medium mb-2 opacity-70">
                    {message.role === 'user' ? '👤 사용자' : '🤖 AI Assistant'}
                  </div>
                  <div className="whitespace-pre-wrap text-base">{message.content}</div>

                  {/* Response Details */}
                  {message.response && (
                    <div className="mt-6 space-y-6">
                      {/* Domain Classification */}
                      <div>
                        <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded mr-2 text-xs">Layer 1</span>
                          도메인 분류 결과
                        </h3>
                        <DomainClassificationDisplay
                          classification={convertToDomainClassification(message.response)}
                        />
                        <p className="text-xs text-gray-600 mt-2">
                          💡 질문 키워드를 분석하여 Security, Conversion, Marketing, General 중 가장 적합한 도메인을 자동으로 분류합니다.
                        </p>
                      </div>

                      {/* Process Flow */}
                      <div>
                        <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center">
                          <span className="bg-green-100 text-green-800 px-2 py-1 rounded mr-2 text-xs">전체 프로세스</span>
                          4-Layer 실행 흐름
                        </h3>
                        <UnifiedProcessFlow
                          steps={convertToProcessSteps(message.response)}
                        />
                        <p className="text-xs text-gray-600 mt-2">
                          💡 Layer 1(도메인 분류) → Layer 2(도메인별 컨텍스트 로드) → Layer 3(실행 모드 결정) → Layer 4(에이전트 실행) 순서로 진행됩니다.
                        </p>
                      </div>

                      {/* Analysis Steps */}
                      {message.response.analysis_steps && message.response.analysis_steps.length > 0 && (
                        <div className="bg-gray-50 rounded-lg p-4">
                          <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                            <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded mr-2 text-xs">분석 과정</span>
                            단계별 추론
                          </h4>
                          <ul className="space-y-2">
                            {message.response.analysis_steps.map((step, idx) => (
                              <li key={idx} className="text-sm text-gray-700 flex">
                                <span className="font-medium text-purple-600 mr-2">{idx + 1}.</span>
                                <span>{step}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* SQL Query */}
                      {message.response.sql_query && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                            <span className="bg-gray-800 text-white px-2 py-1 rounded mr-2 text-xs">SQL</span>
                            생성된 쿼리
                          </h4>
                          <div className="bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-sm overflow-x-auto">
                            {message.response.sql_query}
                          </div>
                          <p className="text-xs text-gray-600 mt-2">
                            💡 Layer 4에서 선택된 에이전트({message.response.adk_agent || 'BigQuery Agent'})가
                            {message.response.adk_model || 'Gemini'} 모델을 사용하여 생성한 SQL입니다.
                          </p>
                        </div>
                      )}

                      {/* Vision Analysis Result */}
                      {message.response.execution_trace?.some(trace => trace.phase === 'adk_tool_call' && trace.response_summary?.vision_analysis) && (
                        <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-100">
                          <h4 className="text-sm font-semibold text-indigo-900 mb-3 flex items-center">
                            <span className="bg-indigo-600 text-white px-2 py-1 rounded mr-2 text-xs">Vision</span>
                            이미지 분석 결과 (Gemini Files API)
                          </h4>
                          
                          {message.response.execution_trace
                            .filter(trace => trace.phase === 'adk_tool_call' && trace.response_summary?.vision_analysis)
                            .map((trace, idx) => {
                              const vision = trace.response_summary?.vision_analysis as any;
                              return (
                                <div key={idx} className="space-y-3">
                                  <div className="flex items-center text-xs text-indigo-700 bg-indigo-100 px-2 py-1 rounded w-fit">
                                    <span className="font-medium mr-2">파일명:</span>
                                    {vision?.file_info?.name}
                                    <span className="mx-2">|</span>
                                    <span className="font-medium mr-2">크기:</span>
                                    {vision?.file_info?.size_kb?.toFixed(2)} KB
                                  </div>
                                  
                                  <div className="bg-white rounded border border-indigo-200 p-3">
                                    <div className="text-xs font-semibold text-gray-500 mb-1">OCR 추출 텍스트</div>
                                    <div className="text-sm text-gray-800 whitespace-pre-wrap max-h-40 overflow-y-auto custom-scrollbar">
                                      {vision?.ocr_text || "(텍스트 없음)"}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                        </div>
                      )}

                      {/* Agent & Model Info */}
                      {(message.response.adk_agent || message.response.adk_model) && (
                        <div className="bg-blue-50 rounded-lg p-4">
                          <h4 className="text-sm font-semibold text-gray-900 mb-2">실행 정보</h4>
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            {message.response.adk_agent && (
                              <div>
                                <span className="text-gray-600">에이전트:</span>
                                <span className="ml-2 font-medium text-gray-900">{message.response.adk_agent}</span>
                              </div>
                            )}
                            {message.response.adk_model && (
                              <div>
                                <span className="text-gray-600">모델:</span>
                                <span className="ml-2 font-medium text-gray-900">{message.response.adk_model}</span>
                              </div>
                            )}
                            {message.response.execution_time && (
                              <div>
                                <span className="text-gray-600">실행 시간:</span>
                                <span className="ml-2 font-medium text-gray-900">{message.response.execution_time.toFixed(2)}초</span>
                              </div>
                            )}
                            {message.response.execution_mode && (
                              <div>
                                <span className="text-gray-600">실행 모드:</span>
                                <span className="ml-2 font-medium text-gray-900">{message.response.execution_mode}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white rounded-lg p-4 shadow">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 bg-white p-4">
            <div className="flex gap-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="질문을 입력하세요. 예: '최근 7일간 스미싱 탐지 건수를 보여줘', '이번 달 전환율은 얼마야?'"
                className="flex-1 p-4 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
                rows={3}
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="px-8 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium transition-colors"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>분석 중...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    전송
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default UnifiedChatInterface
