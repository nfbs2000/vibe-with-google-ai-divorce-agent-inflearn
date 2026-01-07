import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Sidebar } from './components/Sidebar'
import {
  Message,
  DataSource,
  SystemStatus,
  AgentSummary,
  AgentMetadata,
  SqlGenerationDetails,
  Domain,
} from './types'
import { apiService } from './services/api'
import type { SSEEvent } from './services/api'
import { toast, Toaster } from 'sonner'
import { ConversationHeader } from './components/ConversationHeader'
import { QuickActionsPanel } from './components/QuickActionsPanel'
import { MessageSection } from './components/MessageSection'
import { ChatInput } from './components/ChatInput'
import { LogPanel } from './components/LogPanel'
import type { LogEntry } from './components/LogPanel'
import { trackPageView, trackAgentChatStart, trackAgentQuery, trackAgentResponse } from './lib/analytics'

type LogSource = 'frontend' | 'backend'

const DIVORCE_CASE_QUICK_QUERIES: Array<{ label: string; value: string; tone: 'blue' | 'violet' | 'emerald' | 'amber' | 'red' | 'orange' }> = [
  {
    label: '📸 부정행위 증거 분석',
    value: '이 사진(영수증/문자)이 부정행위 증거가 될 수 있는지 분석해줘.',
    tone: 'red'
  },
  {
    label: '⚖️ 위자료 산정 기준',
    value: '배우자의 부정행위로 인한 위자료 산정 기준과 최근 판례 경향을 알려줘.',
    tone: 'blue'
  },
  {
    label: '🧒 양육권 판단 기준',
    value: '양육권 소송에서 가장 중요하게 고려되는 요소가 뭐야?',
    tone: 'emerald'
  },
  {
    label: '💰 재산분할 기여도',
    value: '혼인 기간 10년 차 맞벌이 부부의 재산분할 비율은 보통 어떻게 돼?',
    tone: 'amber'
  },
  {
    label: '📄 증거 수집 주의사항',
    value: '불법적이지 않게 이혼 소송 증거를 수집하는 방법은?',
    tone: 'orange'
  }
]




const SQL_MODE_PRESETS: Record<string, { label: string; advantages: string[] }> = {
  schema_aware: {
    label: 'Schema-Aware SQL',
    advantages: [
      'BigQuery 스키마를 실시간으로 로드',
      '테이블 관계 메타데이터로 JOIN 가이드를 제공',
      'Gemini가 순수 SQL을 생성하여 복잡한 쿼리 대응',
    ],
  },
  template: {
    label: 'Template SQL',
    advantages: [
      '도메인별 템플릿으로 신속하게 쿼리를 구성',
      '일관된 패턴으로 예측 가능한 실행 비용',
      'LLM 호출 없이도 안정적으로 동작',
    ],
  },
  adk: {
    label: 'ADK Agent',
    advantages: [
      'Google ADK가 도구 호출과 결과 해석을 자동화',
      'Dry-run으로 스키마를 검증한 뒤 안전하게 실행',
      '응답과 분석 노트를 자동으로 생성',
    ],
  },
}

const describeSqlMode = (mode?: string | null): string => {
  if (!mode) return 'SQL 엔진'
  return SQL_MODE_PRESETS[mode]?.label ?? 'SQL 엔진'
}

function App() {
  const [domain, setDomain] = useState<Domain>('divorce_case')
  const [agentType, setAgentType] = useState<'sql' | 'conversational'>('sql')
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const currentModelName = systemStatus?.model_name ?? 'gemini-2.0-flash'
  const [exampleQueries, setExampleQueries] = useState<string[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [agents, setAgents] = useState<AgentSummary[]>([])
  const [activeAgent, setActiveAgent] = useState<AgentMetadata | null>(null)
  const [sqlSummary, setSqlSummary] = useState<SqlGenerationDetails | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)

  const appendLog = useCallback((source: LogSource, message: string) => {
    setLogs(prev => {
      const entry: LogEntry = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        source,
        message,
        timestamp: new Date()
      }
      const next = [...prev, entry]
      return next.length > 300 ? next.slice(-300) : next
    })
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    appendLog('frontend', '세션이 시작되었습니다.')
  }, [appendLog])
  const disableAutoScroll = useRef(false)

  const findAgentByKey = useCallback(
    (key?: string | null) => {
      if (!key) return null
      return agents.find((agent) => agent.key === key) ?? null
    },
    [agents]
  )

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (disableAutoScroll.current) {
      return
    }
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const loadInitialData = useCallback(async () => {
    try {
      appendLog('frontend', '초기 데이터 로딩 중...')
      const [sources, status, generalExamples, agentList] = await Promise.all([
        apiService.getDataSources(),
        apiService.getSystemStatus(),
        apiService.getExampleQueries(),
        apiService.getAgents()
      ])

      setDataSources(sources)
      setSystemStatus(status)
      setExampleQueries(generalExamples)
      setAgents(agentList)

      const initialAgent =
        agentList.find((agent) => agent.key === 'divorce_case') ??
        agentList.find((agent) => agent.active) ??
        agentList[0] ??
        null
      setActiveAgent(initialAgent)

      appendLog('frontend', '초기 데이터 로딩 완료')

      // 페이지뷰 추적
      trackPageView(window.location.pathname, 'BigQuery Agent Demo')
    } catch (error) {
      console.error('Failed to load initial data:', error)
      appendLog('frontend', '초기 데이터 로딩 실패: 네트워크 또는 백엔드 상태를 확인하세요.')
      toast.error('초기 데이터 로드에 실패했습니다.')
    }
  }, [appendLog])

  useEffect(() => {
    void loadInitialData()
  }, [loadInitialData])

  const handleExampleQuery = (query: string) => {
    handleDomainChange('general')
    setInputValue(query)
    appendLog('frontend', `샘플 질문 선택: "${query}"`)
  }

  const handleQuickQuery = (value: string) => {
    setInputValue(value)
  }

  const handleFeedback = async (messageId: string, type: 'like' | 'dislike') => {
    try {
      await apiService.sendFeedback({
        message_id: messageId,
        feedback_type: type,
        user_id: 'demo-user'
      })
      toast.success(type === 'like' ? '좋아요를 보냈습니다!' : '피드백을 보냈습니다!')
    } catch (error) {
      console.error('Failed to send feedback:', error)
      appendLog('frontend', `피드백 전송 실패: ${(error as Error)?.message ?? '알 수 없는 오류'}`)
      toast.error('피드백 전송에 실패했습니다.')
    }
  }

  const handleDomainChange = useCallback((nextDomain: typeof domain) => {
    setDomain(nextDomain)
    appendLog('frontend', `도메인 전환: ${nextDomain}`)
    if (agentType === 'sql') {
      const domainAgent = findAgentByKey(nextDomain)
      setActiveAgent(domainAgent)
      setSqlSummary(null)
    }
  }, [agentType, appendLog, findAgentByKey])

  const handleAgentTypeChange = useCallback((type: typeof agentType) => {
    if (type === agentType) return
    setAgentType(type)
    setSqlSummary(null)
    appendLog(
      'frontend',
      type === 'conversational'
        ? 'Conversational Agent 모드를 선택했습니다. AI가 자연어로 인사이트를 생성합니다.'
        : 'SQL Agent 모드를 선택했습니다. BigQuery 도구로 직접 분석합니다.'
    )
    if (type === 'conversational') {
      setActiveAgent(findAgentByKey('conversational'))
    } else {
      setActiveAgent(findAgentByKey('divorce_case'))
    }

    // 에이전트 대화 시작 추적
    trackAgentChatStart(type)
  }, [agentType, appendLog, domain, findAgentByKey])

  const submitGeneral = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed && files.length === 0) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: trimmed + (files.length > 0 ? `\n(첨부파일 ${files.length}개)` : ''),
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    const modeLabel = agentType === 'conversational' ? 'Conversational Agent' : 'SQL Agent'

    appendLog('frontend', `질문 전송: "${trimmed}"`)
    appendLog('frontend', `실행 모드: ${modeLabel}`)

    setInputValue('')
    setFiles([])
    setIsLoading(true)

    // 1. Upload files first
    let uploadedFilePaths: string[] = []
    if (files.length > 0) {
      appendLog('frontend', `📤 파일 업로드 중... (${files.length}개)`)
      try {
        const uploadPromises = files.map(f => apiService.uploadFile(f))
        const results = await Promise.all(uploadPromises)
        uploadedFilePaths = results.map(r => r.file_path)
        appendLog('frontend', `✅ 파일 업로드 완료`)
      } catch (err) {
        console.error('File upload failed:', err)
        appendLog('frontend', `❌ 파일 업로드 실패: ${err}`)
        toast.error('파일 업로드 실패')
        setIsLoading(false)
        return
      }
    }

    trackAgentQuery(agentType, trimmed.length)

    // 2. Prepare assistant message placeholder
    const assistantId = (Date.now() + 1).toString()
    const assistantMessage: Message = {
      id: assistantId,
      content: '', // Start empty, will stream in
      sender: 'assistant',
      timestamp: new Date(),
      queryResult: {
        response: '',
        data: [],
        chart_type: 'table',
        sql_mode: agentType === 'conversational' ? 'conversational' : 'adk'
      }
    }
    setMessages(prev => [...prev, assistantMessage])

    // Streaming variables
    let agentResponse = ''
    let sqlQuery: string | null = null
    let queryResultData: any[] = []
    let agentInfoMeta: AgentMetadata | null = null
    let streamMode = agentType === 'conversational' ? 'conversational' : 'adk'
    const queryStartTime = Date.now()

    appendLog('frontend', '🔌 SSE 연결 시작...')

    try {
      apiService.streamQuery(
        {
          query: trimmed || '증거 분석을 요청합니다.',
          user_id: 'demo-user',
          session_id: 'demo-session',
          agent_type: agentType,
          files: uploadedFilePaths.length > 0 ? uploadedFilePaths : undefined,
        },
        (event: SSEEvent) => {
          const { event: eventType, data } = event

          switch (eventType) {
            case 'start':
              appendLog('backend', `🚀 스트리밍 시작`)
              break

            case 'agent_info':
              if (typeof data === 'object' && data !== null) {
                const info = data as any
                appendLog('backend', `🤖 에이전트: ${info.agent_name} (${info.agent_display_name})`)

                const matchedAgent =
                  findAgentByKey(info.agent_key) ??
                  agents.find(a => a.key === info.agent_name || a.display_name === info.agent_name)

                if (matchedAgent) {
                  agentInfoMeta = matchedAgent
                  setActiveAgent(matchedAgent)
                }
              }
              break

            case 'debug':
              if (typeof data === 'object' && data !== null) {
                const dbg = data as any
                // 상세 디버그 로그가 너무 많으면 부담스러울 수 있으므로, 
                // 특정 중요 이벤트나 상태 변화만 로그로 남기거나, 
                // 사용자 요청대로 모든 debug 패킷을 간략히 표시
                appendLog('backend', `🐞 Debug [${dbg.event_type}]: ${dbg.role || 'system'} (parts: ${dbg.parts_count})`)
              }
              break

            case 'thought':
              // 내부 사고 과정 (로그에만 표시하거나 UI에 표시 가능)
              if (typeof data === 'object' && data !== null) {
                const thought = (data as any).thought
                appendLog('backend', `💡 사고: ${thought}`)
              }
              break

            case 'thinking':
              if (typeof data === 'object' && data !== null) {
                const text = (data as any).text
                if (text) {
                  agentResponse += text
                  // 실시간 업데이트
                  setMessages(prev => prev.map(m =>
                    m.id === assistantId
                      ? { ...m, content: agentResponse, queryResult: { ...m.queryResult!, response: agentResponse } }
                      : m
                  ))
                }
              }
              break

            case 'tool_call':
              if (typeof data === 'object' && data !== null) {
                const tc = data as any
                const argsStr = JSON.stringify(tc.args, null, 2)
                appendLog('backend', `🛠️ 도구 호출: ${tc.tool_name}\nArgs: ${argsStr}`)
              }
              break

            case 'sql':
              if (typeof data === 'object' && data !== null) {
                const sqlEvent = data as any
                sqlQuery = sqlEvent.sql
                appendLog('backend', `💾 SQL 생성됨:\n${sqlQuery}`)
                // SQL 정보 업데이트
                setMessages(prev => prev.map(m =>
                  m.id === assistantId
                    ? { ...m, queryResult: { ...m.queryResult!, sql: sqlQuery ?? undefined } }
                    : m
                ))
              }
              break

            case 'result':
              if (typeof data === 'object' && data !== null) {
                const res = data as any
                if (res.preview) {
                  queryResultData = res.preview
                  const previewStr = JSON.stringify(res.preview, null, 2)
                  appendLog('backend', `📊 결과 (${res.row_count}건):\n${previewStr}`)
                  // 결과 데이터 업데이트
                  setMessages(prev => prev.map(m =>
                    m.id === assistantId
                      ? { ...m, queryResult: { ...m.queryResult!, data: queryResultData } }
                      : m
                  ))
                }
              }
              break

            case 'response':
              if (typeof data === 'object' && data !== null) {
                const finalRes = (data as any).response
                if (finalRes) {
                  agentResponse = finalRes // 덮어쓰기 (최종본)
                  setMessages(prev => prev.map(m =>
                    m.id === assistantId
                      ? { ...m, content: agentResponse, queryResult: { ...m.queryResult!, response: agentResponse } }
                      : m
                  ))
                  appendLog('backend', `✅ 최종 응답 수신`)
                }
              }
              break

            case 'done': {
              const doneData = data as any
              if (doneData?.mode) streamMode = doneData.mode

              appendLog('backend', `🎉 완료 (Time: ${Date.now() - queryStartTime}ms)`)
              setIsLoading(false)
              trackAgentResponse(agentType, Date.now() - queryStartTime, true)

              // 최종 상태 확정 (누락된 메타데이터 등 채우기)
              setMessages(prev => prev.map(m =>
                m.id === assistantId
                  ? {
                    ...m,
                    content: agentResponse || '완료되었습니다.',
                    queryResult: {
                      ...m.queryResult!,
                      response: agentResponse || '완료되었습니다.',
                      data: queryResultData,
                      sql: sqlQuery ?? undefined,
                      sql_mode: streamMode as any,
                      adk_agent: agentInfoMeta?.display_name ?? 'ADK Agent',
                      adk_model: agentInfoMeta?.model ?? currentModelName,
                      agent_metadata: agentInfoMeta ?? undefined
                    }
                  }
                  : m
              ))

              setSqlSummary({
                sql_preview: sqlQuery ?? '',
                reason: 'Generated by Agent',
                mode: streamMode as any
              })
              break
            }

            case 'error':
              const errorMsg = (data as any)?.error || 'Unknown Error'
              appendLog('backend', `❌ 에러: ${errorMsg}`)
              toast.error(errorMsg)
              setIsLoading(false)
              trackAgentResponse(agentType, Date.now() - queryStartTime, false)

              // 에러 메시지로 교체
              setMessages(prev => prev.map(m =>
                m.id === assistantId
                  ? { ...m, content: `오류가 발생했습니다: ${errorMsg}`, sender: 'error' }
                  : m
              ))
              break
          }
        }
      )
    } catch (error) {
      console.error('Steam error:', error)
      setIsLoading(false)
      toast.error('연결 실패')
    }
  }, [agentType, appendLog, agents, files, findAgentByKey, currentModelName])

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()
    const trimmed = inputValue.trim()
    if ((!trimmed && files.length === 0) || isLoading) return
    void submitGeneral(trimmed)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const executedModeLabel = useMemo(() => {
    if (agentType === 'conversational') {
      return 'Conversational Agent'
    }
    if (sqlSummary?.mode) {
      return describeSqlMode(sqlSummary.mode)
    }
    return 'SQL Agent'
  }, [agentType, sqlSummary])

  const isBusy = isLoading

  const quickQueries = DIVORCE_CASE_QUICK_QUERIES


  return (
    <div className="flex h-screen bg-gray-50">
      <Toaster position="top-right" richColors />

      <Sidebar
        dataSources={dataSources}
        systemStatus={systemStatus}
        onExampleQuery={handleExampleQuery}
        exampleQueries={exampleQueries}
      />

      <div className="flex-1 flex flex-col">
        <ConversationHeader
          agentType={agentType}
          onAgentTypeChange={handleAgentTypeChange}
          executedModeLabel={executedModeLabel}
        />

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <QuickActionsPanel
            domain={domain}
            executedModeLabel={executedModeLabel}
            quickQueries={quickQueries}
            isBusy={isBusy}
            onSelect={handleQuickQuery}
            hasMessages={messages.length > 0}
          />

          <MessageSection
            messages={messages}
            isBusy={isBusy}
            onFeedback={handleFeedback}
            messagesEndRef={messagesEndRef}
          />

          <LogPanel logs={logs} logsEndRef={logsEndRef} />
        </div>

        <ChatInput
          domain={domain}
          inputValue={inputValue}
          files={files}
          isBusy={isBusy}
          onChange={setInputValue}
          onFilesChange={setFiles}
          onSubmit={handleSubmit}
          onKeyPress={handleKeyPress}
        />
      </div>
    </div>
  )
}

export default App
