import React, { useState } from 'react'
import { ChevronDown, ChevronUp, Sparkles, Brain, Workflow, CheckCircle2, HelpCircle, Target, Lightbulb } from 'lucide-react'
import { ExecutionTraceItem, ReasoningDetail } from '../types'

interface AnalysisStepsPanelProps {
  analysisSteps?: string[]
  reasoningDetail?: ReasoningDetail
  reasoningFormatted?: string
  executionTrace?: ExecutionTraceItem[]
  className?: string
}

export const AnalysisStepsPanel: React.FC<AnalysisStepsPanelProps> = ({
  analysisSteps,
  reasoningDetail,
  reasoningFormatted,
  executionTrace,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(true)
  const [showTrace, setShowTrace] = useState(false)
  const [showDetailedReasoning, setShowDetailedReasoning] = useState(false)

  // 표시할 데이터가 없으면 null 반환
  if ((!analysisSteps || analysisSteps.length === 0) && !reasoningDetail) {
    return null
  }

  // Reasoning phase 아이콘 매핑
  const reasoningPhaseIcons: Record<string, React.ReactNode> = {
    question_analysis: <HelpCircle className="w-4 h-4" />,
    table_selection: <Sparkles className="w-4 h-4" />,
    query_strategy: <Target className="w-4 h-4" />,
    insight_derivation: <Lightbulb className="w-4 h-4" />,
  }

  const reasoningPhaseColors: Record<string, string> = {
    question_analysis: 'bg-blue-100 text-blue-700',
    table_selection: 'bg-purple-100 text-purple-700',
    query_strategy: 'bg-amber-100 text-amber-700',
    insight_derivation: 'bg-emerald-100 text-emerald-700',
    default: 'bg-slate-100 text-slate-700',
  }

  const reasoningPhaseNames: Record<string, string> = {
    question_analysis: '질문 분석',
    table_selection: '테이블 선정',
    query_strategy: '쿼리 전략',
    insight_derivation: '인사이트 도출',
  }

  const phaseIcons: Record<string, React.ReactNode> = {
    agent_selection: <Sparkles className="w-4 h-4" />,
    adk_tool_call: <Workflow className="w-4 h-4" />,
    sql_generated: <CheckCircle2 className="w-4 h-4" />,
    query_execution: <CheckCircle2 className="w-4 h-4" />,
    agent_response: <Brain className="w-4 h-4" />,
  }

  const phaseColors: Record<string, string> = {
    agent_selection: 'bg-indigo-100 text-indigo-700',
    adk_tool_call: 'bg-amber-100 text-amber-700',
    sql_generated: 'bg-blue-100 text-blue-700',
    query_execution: 'bg-purple-100 text-purple-700',
    agent_response: 'bg-rose-100 text-rose-700',
    default: 'bg-slate-100 text-slate-700',
  }

  const stepCount = reasoningDetail?.total_steps || analysisSteps?.length || 0

  return (
    <div className={`bg-gradient-to-br from-slate-50 to-blue-50 border border-slate-200 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/50 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <Brain className="w-5 h-5 text-indigo-600" />
          <h3 className="text-sm font-semibold text-slate-900">AI 사고 과정</h3>
          <span className="text-xs text-slate-500">({stepCount}단계)</span>
          {reasoningDetail && (
            <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">
              Enhanced
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Detailed Reasoning (if available) */}
          {reasoningDetail && reasoningDetail.steps.length > 0 && (
            <div className="space-y-3">
              {reasoningDetail.steps.map((step) => {
                const phaseIcon = reasoningPhaseIcons[step.phase] || <Brain className="w-4 h-4" />
                const phaseColor = reasoningPhaseColors[step.phase] || reasoningPhaseColors.default
                const phaseName = reasoningPhaseNames[step.phase] || step.phase

                return (
                  <div
                    key={step.step_number}
                    className="bg-white rounded-lg p-3 border border-slate-200 hover:border-indigo-200 transition-colors"
                  >
                    <div className="flex items-start space-x-3">
                      <div className={`flex-shrink-0 p-2 rounded ${phaseColor}`}>
                        {phaseIcon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="text-xs font-semibold text-slate-700">
                            {step.step_number}. {phaseName}
                          </span>
                          {step.confidence < 1.0 && (
                            <span className="text-xs text-slate-500">
                              (신뢰도: {(step.confidence * 100).toFixed(0)}%)
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
                          {step.thought}
                        </p>
                        {showDetailedReasoning && step.metadata && Object.keys(step.metadata).length > 0 && (
                          <div className="mt-2 pt-2 border-t border-slate-100">
                            <pre className="text-xs text-slate-500 overflow-x-auto">
                              {JSON.stringify(step.metadata, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}

              {/* Toggle for detailed metadata */}
              {reasoningDetail.steps.some(s => s.metadata && Object.keys(s.metadata).length > 0) && (
                <button
                  onClick={() => setShowDetailedReasoning(!showDetailedReasoning)}
                  className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  {showDetailedReasoning ? '메타데이터 숨기기' : '메타데이터 보기'}
                </button>
              )}
            </div>
          )}

          {/* Fallback to analysis steps if no detailed reasoning */}
          {!reasoningDetail && analysisSteps && analysisSteps.length > 0 && (
            <div className="space-y-2">
              {analysisSteps.map((step, index) => (
                <div
                  key={index}
                  className="flex items-start space-x-3 text-sm group"
                >
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-xs font-semibold mt-0.5">
                    {index + 1}
                  </div>
                  <p className="flex-1 text-slate-700 leading-relaxed group-hover:text-slate-900 transition-colors">
                    {step}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Execution Trace Toggle */}
          {executionTrace && executionTrace.length > 0 && (
            <div className="pt-2 border-t border-slate-200">
              <button
                onClick={() => setShowTrace(!showTrace)}
                className="text-xs text-indigo-600 hover:text-indigo-700 font-medium flex items-center space-x-1"
              >
                <Workflow className="w-3 h-3" />
                <span>{showTrace ? '실행 추적 숨기기' : '실행 추적 보기'}</span>
                <span className="text-slate-400">({executionTrace.length})</span>
              </button>

              {showTrace && (
                <div className="mt-3 space-y-2">
                  {executionTrace.map((trace, index) => {
                    const phaseColor = phaseColors[trace.phase] || phaseColors.default
                    const phaseIcon = phaseIcons[trace.phase] || <Workflow className="w-4 h-4" />

                    return (
                      <div
                        key={index}
                        className="bg-white rounded-lg p-3 border border-slate-200"
                      >
                        <div className="flex items-center space-x-2 mb-2">
                          <div className={`p-1.5 rounded ${phaseColor}`}>
                            {phaseIcon}
                          </div>
                          <span className="text-xs font-semibold text-slate-700">
                            {trace.phase}
                          </span>
                          {trace.status && (
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              trace.status === 'success' ? 'bg-emerald-100 text-emerald-700' :
                              trace.status === 'failed' ? 'bg-rose-100 text-rose-700' :
                              'bg-amber-100 text-amber-700'
                            }`}>
                              {trace.status}
                            </span>
                          )}
                        </div>

                        {/* Trace Details */}
                        <div className="text-xs text-slate-600 space-y-1">
                          {trace.tool_name && (
                            <p>🛠️ Tool: <span className="font-medium">{trace.tool_name}</span></p>
                          )}
                          {trace.row_count !== undefined && (
                            <p>📊 Rows: <span className="font-medium">{trace.row_count}</span></p>
                          )}
                          {trace.executor && (
                            <p>⚙️ Executor: <span className="font-medium">{trace.executor}</span></p>
                          )}
                          {trace.sql_preview && (
                            <div className="mt-2">
                              <p className="text-slate-500 mb-1">SQL Preview:</p>
                              <pre className="bg-slate-100 p-2 rounded text-[10px] overflow-x-auto">
                                {trace.sql_preview}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
