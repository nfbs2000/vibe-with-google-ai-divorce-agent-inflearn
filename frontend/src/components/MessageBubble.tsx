import React from 'react'
import { Bot, User, AlertCircle, Copy, ThumbsUp, ThumbsDown, Sparkles, Workflow, Code, Database, Scale } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { ExecutionTraceItem, Message, SqlGenerationDetails } from '../types'
import { AnalysisStepsPanel } from './AnalysisStepsPanel'

// Domain icon mapping
const DOMAIN_ICONS = {
  general: <Database className="w-4 h-4" />,
  divorce_case: <Scale className="w-4 h-4" />
}

const DOMAIN_LABELS = {
  general: '범용 데이터 분석',
  divorce_case: '이혼 사례 분석'
}

const DOMAIN_COLORS = {
  general: { bg: 'from-gray-50 to-slate-50', border: 'border-gray-200', text: 'text-gray-600', labelText: 'text-gray-900' },
  divorce_case: { bg: 'from-indigo-50 to-blue-50', border: 'border-indigo-200', text: 'text-indigo-600', labelText: 'text-indigo-900' }
}

const MODE_SUMMARY_STYLES: Record<
  string,
  { border: string; header: string; chip: string; icon: string }
> = {
  schema_aware: {
    border: 'border-emerald-200 bg-white',
    header: 'text-emerald-700',
    chip: 'bg-emerald-50 text-emerald-700 border border-emerald-100',
    icon: 'text-emerald-500',
  },
  template: {
    border: 'border-blue-200 bg-white',
    header: 'text-blue-700',
    chip: 'bg-blue-50 text-blue-700 border border-blue-100',
    icon: 'text-blue-500',
  },
  adk: {
    border: 'border-amber-200 bg-white',
    header: 'text-amber-700',
    chip: 'bg-amber-50 text-amber-700 border border-amber-100',
    icon: 'text-amber-500',
  },
  default: {
    border: 'border-slate-200 bg-white',
    header: 'text-slate-700',
    chip: 'bg-slate-50 text-slate-600 border border-slate-100',
    icon: 'text-slate-500',
  },
}

const ATTEMPT_STATUS_CLASS: Record<string, string> = {
  success: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
  failed: 'bg-rose-100 text-rose-700 border border-rose-200',
  pending: 'bg-amber-100 text-amber-700 border border-amber-200',
  default: 'bg-slate-100 text-slate-600 border border-slate-200',
}

const PHASE_COLOR: Record<string, string> = {
  agent_selection: 'bg-indigo-400',
  adk_tool_call: 'bg-amber-400',
  schema_aware_prepare: 'bg-emerald-400',
  sql_generated: 'bg-blue-400',
  query_execution: 'bg-purple-400',
  result_interpretation: 'bg-slate-400',
  chart_suggestion: 'bg-pink-400',
  agent_response: 'bg-rose-400',
  default: 'bg-slate-300',
}

const describeSqlMode = (mode?: string | null): string => {
  switch (mode) {
    case 'schema_aware':
      return 'Schema-Aware SQL'
    case 'template':
      return 'Template SQL'
    case 'adk':
      return 'ADK Agent'
    default:
      return 'SQL 엔진'
  }
}

const statusBadgeClass = (status?: string): string => {
  if (!status) return ATTEMPT_STATUS_CLASS.default
  const key = status.toLowerCase()
  return ATTEMPT_STATUS_CLASS[key] ?? ATTEMPT_STATUS_CLASS.default
}

const summarizeResponseSummary = (summary?: Record<string, unknown>): string[] => {
  if (!summary) return []
  const details: string[] = []
  if (typeof summary.row_count === 'number') {
    details.push(`행 ${summary.row_count}`)
  }
  if (typeof summary.schema_fields === 'number') {
    details.push(`필드 ${summary.schema_fields}`)
  }
  if (typeof summary.total_bytes_processed === 'number') {
    const mb = summary.total_bytes_processed / (1024 * 1024)
    details.push(`드라이런 ${mb.toFixed(1)} MB`)
  }
  Object.entries(summary).forEach(([key, value]) => {
    if (
      ['row_count', 'schema_fields', 'total_bytes_processed'].includes(key) ||
      value === undefined ||
      value === null
    ) {
      return
    }
    if (typeof value === 'string' && value.trim()) {
      details.push(`${key}: ${value}`)
    } else if (typeof value === 'number') {
      details.push(`${key}: ${value}`)
    }
  })
  return details.slice(0, 3)
}

const formatTraceItem = (item: ExecutionTraceItem, index: number) => {
  const details: string[] = []
  let title = `단계 ${index + 1}`
  let description = ''

  switch (item.phase) {
    case 'agent_selection': {
      title = '에이전트 선택'
      if (item.agent?.display_name) {
        description = item.agent.display_name
      }
      if (item.reason) {
        details.push(item.reason)
      }
      break
    }
    case 'adk_tool_call': {
      title = item.order ? `ADK 도구 호출 #${item.order}` : 'ADK 도구 호출'
      description = item.tool_name ?? '활성화된 도구'
      const summaryDetails = summarizeResponseSummary(
        item.response_summary as Record<string, unknown> | undefined
      )
      details.push(...summaryDetails)
      if (item.response_preview) {
        details.push(item.response_preview)
      }
      break
    }
    case 'schema_aware_prepare': {
      title = 'Schema-Aware 준비'
      description = `${item.table_count ?? 0}개 테이블 로드`
      if (item.relationship_count) {
        details.push(`관계 ${item.relationship_count}개`)
      }
      break
    }
    case 'sql_generated': {
      title = 'SQL 생성'
      description = describeSqlMode(item.mode)
      if (item.sql_preview) {
        details.push(item.sql_preview.slice(0, 120) + (item.sql_preview.length > 120 ? '…' : ''))
      }
      break
    }
    case 'query_execution': {
      title = '쿼리 실행'
      description = item.executor === 'backend' ? '백엔드 실행' : 'ADK 실행'
      if (typeof item.row_count === 'number') {
        details.push(`행 ${item.row_count}`)
      }
      if (item.status === 'failed' && item.error) {
        details.push(`오류: ${item.error}`)
      }
      break
    }
    case 'result_interpretation': {
      title = '결과 해석'
      description = 'NLP 해석'
      if (typeof item.character_count === 'number') {
        details.push(`응답 ${item.character_count}자`)
      }
      break
    }
    case 'chart_suggestion': {
      title = '차트 추천'
      description = item.chart_type ? item.chart_type.toUpperCase() : '추천 생성'
      break
    }
    case 'agent_response': {
      title = 'ADK 응답 정리'
      description = item.source ?? '최종 응답'
      break
    }
    default: {
      description = item.phase
    }
  }

  const color = PHASE_COLOR[item.phase] ?? PHASE_COLOR.default

  return { title, description, details, color }
}

interface MessageBubbleProps {
  message: Message
  onFeedback?: (messageId: string, type: 'like' | 'dislike') => void
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onFeedback }) => {
  const isUser = message.sender === 'user'
  const isError = message.sender === 'error' || message.isError

  const sqlDetails: SqlGenerationDetails | undefined = message.queryResult?.sql_generation_details
  const executionTrace: ExecutionTraceItem[] =
    Array.isArray(message.queryResult?.execution_trace)
      ? (message.queryResult?.execution_trace as ExecutionTraceItem[])
      : []
  const agentMetadata = message.queryResult?.agent_metadata

  const summaryStyle =
    MODE_SUMMARY_STYLES[sqlDetails?.mode ?? 'default'] ?? MODE_SUMMARY_STYLES.default

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
    } catch (err) {
      console.error('복사 실패:', err)
    }
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser
          ? 'bg-primary-600 text-white'
          : isError
            ? 'bg-red-100 text-red-600'
            : 'bg-gray-100 text-gray-600'
          }`}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : isError ? (
          <AlertCircle className="w-4 h-4" />
        ) : (
          <Bot className="w-4 h-4" />
        )}
      </div>

      <div className={`flex-1 max-w-3xl ${isUser ? 'flex flex-col items-end' : ''}`}>
        {!isUser && !isError && (message.queryResult?.adk_agent || message.queryResult?.domain || message.queryResult?.execution_mode) && (
          <div className="mb-2 space-y-2">
            {/* Domain Info */}
            {message.queryResult.domain && (
              <div className={`flex items-center space-x-2 px-3 py-1.5 bg-gradient-to-r ${DOMAIN_COLORS[message.queryResult.domain as keyof typeof DOMAIN_COLORS]?.bg || DOMAIN_COLORS.general.bg} border ${DOMAIN_COLORS[message.queryResult.domain as keyof typeof DOMAIN_COLORS]?.border || DOMAIN_COLORS.general.border} rounded-lg`}>
                <span className={DOMAIN_COLORS[message.queryResult.domain as keyof typeof DOMAIN_COLORS]?.text || DOMAIN_COLORS.general.text}>
                  {DOMAIN_ICONS[message.queryResult.domain as keyof typeof DOMAIN_ICONS] || DOMAIN_ICONS.general}
                </span>
                <div className="flex flex-col">
                  <span className={`text-xs font-semibold ${DOMAIN_COLORS[message.queryResult.domain as keyof typeof DOMAIN_COLORS]?.labelText || DOMAIN_COLORS.general.labelText}`}>
                    🎯 Domain
                  </span>
                  <span className={`text-xs ${DOMAIN_COLORS[message.queryResult.domain as keyof typeof DOMAIN_COLORS]?.text || DOMAIN_COLORS.general.text}`}>
                    {DOMAIN_LABELS[message.queryResult.domain as keyof typeof DOMAIN_LABELS] || message.queryResult.domain}
                    {message.queryResult.domain_confidence !== undefined && (
                      <span className="ml-1 opacity-75">
                        • {Math.round(message.queryResult.domain_confidence * 100)}%
                      </span>
                    )}
                  </span>
                </div>
              </div>
            )}

            {/* Agent Info */}
            {message.queryResult.adk_agent && (
              <div className="flex items-center space-x-2 px-3 py-1.5 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg">
                <Sparkles className="w-4 h-4 text-blue-600" />
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-blue-900">
                    🤖 Agent & Model
                  </span>
                  <span className="text-xs text-blue-700">
                    {agentMetadata?.display_name ?? message.queryResult.adk_agent}
                    {message.queryResult.adk_model ? ` • ${message.queryResult.adk_model}` : ''}
                  </span>
                </div>
              </div>
            )}

            {/* Execution Mode Info */}
            {message.queryResult.execution_mode && (
              <div className="flex items-center space-x-2 px-3 py-1.5 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-lg">
                <Code className="w-4 h-4 text-amber-600" />
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-amber-900">
                    ⚙️ Execution Mode
                  </span>
                  <span className="text-xs text-amber-700">
                    {message.queryResult.execution_mode === 'sql' ? 'SQL 직접 작성' :
                      message.queryResult.execution_mode === 'conversational' ? 'AI 자동 분석' :
                        message.queryResult.execution_mode === 'auto' ? '자동 선택' :
                          message.queryResult.execution_mode}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        <div
          className={`rounded-lg px-4 py-3 ${isUser
            ? 'bg-primary-600 text-white'
            : isError
              ? 'bg-red-50 border border-red-200 text-red-800'
              : 'bg-gray-100 text-gray-900'
            }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  code: ({ children }) => (
                    <code className="bg-gray-200 text-gray-800 px-1 py-0.5 rounded text-xs">
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre className="bg-gray-200 text-gray-800 p-2 rounded text-xs overflow-x-auto">
                      {children}
                    </pre>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        <div
          className={`flex items-center space-x-2 mt-1 text-xs text-gray-500 ${isUser ? 'flex-row-reverse space-x-reverse' : ''
            }`}
        >
          <span>{formatTime(message.timestamp)}</span>

          {message.sender === 'assistant' && !isError && (
            <div className="flex items-center space-x-1">
              <button
                onClick={handleCopy}
                className="p-1 hover:bg-gray-200 rounded transition-colors duration-200"
                title="복사"
              >
                <Copy className="w-3 h-3" />
              </button>
              <button
                onClick={() => onFeedback?.(message.id, 'like')}
                className="p-1 hover:bg-gray-200 rounded transition-colors duration-200"
                title="좋아요"
              >
                <ThumbsUp className="w-3 h-3" />
              </button>
              <button
                onClick={() => onFeedback?.(message.id, 'dislike')}
                className="p-1 hover:bg-gray-200 rounded transition-colors duration-200"
                title="싫어요"
              >
                <ThumbsDown className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {message.queryResult?.sql && (
          <div className="mt-3 bg-gray-900 text-gray-100 rounded-lg p-3 text-sm font-mono overflow-x-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400 uppercase tracking-wide">실행된 SQL</span>
              <button
                onClick={() => navigator.clipboard.writeText(message.queryResult?.sql ?? '')}
                className="text-gray-400 hover:text-gray-200 transition-colors duration-200"
              >
                <Copy className="w-3 h-3" />
              </button>
            </div>
            <pre className="whitespace-pre-wrap">{message.queryResult.sql}</pre>
          </div>
        )}

        {sqlDetails && (
          <div
            className={`mt-3 rounded-lg p-3 border ${summaryStyle.border} shadow-sm`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Sparkles className={`w-4 h-4 ${summaryStyle.icon}`} />
                <div className="flex flex-col">
                  <span className={`text-xs font-semibold uppercase tracking-wide ${summaryStyle.header}`}>
                    SQL 생성 요약
                  </span>
                  <span className="text-xs text-slate-600">
                    {describeSqlMode(sqlDetails.mode)}
                    {sqlDetails.fallback_to
                      ? ` → ${describeSqlMode(sqlDetails.fallback_to)}`
                      : ''}
                  </span>
                </div>
              </div>
              {message.queryResult?.sql_mode && (
                <span className="text-[11px] text-slate-500">
                  요청 모드: {describeSqlMode(message.queryResult.sql_mode)}
                </span>
              )}
            </div>

            {sqlDetails.reason && (
              <div className="mt-2 text-[11px] text-slate-500">{sqlDetails.reason}</div>
            )}

            {Array.isArray(sqlDetails.advantages) && sqlDetails.advantages.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {sqlDetails.advantages.slice(0, 4).map((adv, index) => (
                  <span key={`${adv}-${index}`} className={`px-2 py-0.5 rounded-full text-[11px] ${summaryStyle.chip}`}>
                    {adv}
                  </span>
                ))}
              </div>
            )}

            {Array.isArray(sqlDetails.attempts) && sqlDetails.attempts.length > 0 && (
              <div className="mt-3 space-y-1">
                {sqlDetails.attempts.map((attempt, index) => {
                  const status = attempt.status?.toLowerCase()
                  return (
                    <div
                      key={`${attempt.mode ?? 'attempt'}-${index}`}
                      className="flex items-center justify-between rounded-md bg-slate-50 px-2 py-1 text-[11px] text-slate-600"
                    >
                      <span>
                        {describeSqlMode(attempt.mode ?? null)}
                        {attempt.agent_key ? ` • ${attempt.agent_key}` : ''}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full ${statusBadgeClass(status)}`}>
                        {(status ?? 'status').toUpperCase()}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}

            {sqlDetails.template_metadata && (
              <div className="mt-2 text-[11px] text-slate-500 space-y-1">
                {sqlDetails.template_metadata.provider && (
                  <div>Provider: {sqlDetails.template_metadata.provider}</div>
                )}
                {sqlDetails.template_metadata.model && (
                  <div>Model: {sqlDetails.template_metadata.model}</div>
                )}
                {sqlDetails.template_metadata.fallback_reason && (
                  <div>Fallback 사유: {sqlDetails.template_metadata.fallback_reason}</div>
                )}
              </div>
            )}
          </div>
        )}

        {executionTrace.length > 0 && (
          <div className="mt-3 bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-600 uppercase tracking-wide">
              <Workflow className="w-3 h-3 text-slate-500" />
              <span>실행 타임라인</span>
            </div>
            <ol className="mt-3 space-y-3">
              {executionTrace.map((item, index) => {
                const { title, description, details, color } = formatTraceItem(item, index)
                return (
                  <li key={`${item.phase}-${index}`} className="flex">
                    <div className="flex flex-col items-center mr-3">
                      <div className={`w-2 h-2 rounded-full ${color}`} />
                      {index < executionTrace.length - 1 && (
                        <div className="flex-1 w-px bg-slate-200 mt-1" />
                      )}
                    </div>
                    <div className="flex-1 text-xs text-slate-600">
                      <div className="font-semibold text-slate-700">{title}</div>
                      {description && <div className="mt-0.5">{description}</div>}
                      {details.length > 0 && (
                        <ul className="mt-1 space-y-0.5">
                          {details.map((detail, detailIndex) => (
                            <li key={`${detail}-${detailIndex}`} className="text-[11px] text-slate-500">
                              {detail}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </li>
                )
              })}
            </ol>
          </div>
        )}

        {(message.queryResult?.analysis_steps?.length || message.queryResult?.reasoning_detail) && (
          <AnalysisStepsPanel
            analysisSteps={message.queryResult.analysis_steps}
            reasoningDetail={message.queryResult.reasoning_detail}
            reasoningFormatted={message.queryResult.reasoning_formatted}
            executionTrace={executionTrace}
            className="mt-3"
          />
        )}
      </div>
    </div>
  )
}
