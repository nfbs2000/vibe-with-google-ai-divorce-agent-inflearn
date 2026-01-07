import axios from 'axios'
import {
  QueryRequest,
  QueryResponse,
  DataSource,
  SystemStatus,
  SaaSQueryRequest,
  ChartType,
  AgentSummary,
  AgentMetadata,
  SqlGenerationDetails,
  ExecutionTraceItem,
  SqlGenerationMode,
  SqlGenerationAttempt,
  TemplateGenerationMetadata,
  UnifiedQueryRequest,
  UnifiedQueryResponse,
} from '../types'
import { logger } from '../utils/logger'

// Axios config 타입 확장
declare module 'axios' {
  interface AxiosRequestConfig {
    metadata?: {
      startTime: number
    }
  }

  interface InternalAxiosRequestConfig {
    metadata?: {
      startTime: number
    }
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const toRecordArray = (value: unknown): Record<string, unknown>[] =>
  Array.isArray(value) ? value.filter(isRecord) : []

const toStringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : []

const toSqlMode = (value: unknown): 'template' | 'schema_aware' | 'adk' | 'conversational' | undefined => {
  if (value === 'template' || value === 'schema_aware' || value === 'adk' || value === 'conversational') {
    return value
  }
  if (typeof value === 'string') {
    const lower = value.toLowerCase()
    if (['template', 'schema_aware', 'adk', 'conversational'].includes(lower)) {
      return lower
    }
  }
  return undefined
}

const toAgentMetadata = (value: unknown): AgentMetadata | undefined => {
  if (!isRecord(value)) return undefined
  const key = typeof value.key === 'string' ? value.key : undefined
  const displayName = typeof value.display_name === 'string' ? value.display_name : undefined
  const description = typeof value.description === 'string' ? value.description : undefined
  const focus = typeof value.focus === 'string' ? value.focus : undefined

  if (!key || !displayName || !description || !focus) {
    return undefined
  }

  const strengths = toStringArray(value.strengths)
  const keywords = toStringArray(value.keywords)

  return {
    key,
    display_name: displayName,
    description,
    focus,
    strengths: strengths.length > 0 ? strengths : undefined,
    keywords: keywords.length > 0 ? keywords : undefined,
  }
}

const toSqlModeEnum = (value: unknown): SqlGenerationMode | undefined => {
  if (typeof value !== 'string') return undefined
  const lower = value.toLowerCase()
  if (lower === 'adk' || lower === 'schema_aware' || lower === 'template') {
    return lower
  }
  return 'unknown'
}

const toSqlGenerationAttempt = (value: unknown): SqlGenerationAttempt | null => {
  if (!isRecord(value)) return null
  const attempt: SqlGenerationAttempt = {
    mode: typeof value.mode === 'string' ? value.mode : undefined,
    status: typeof value.status === 'string' ? value.status : undefined,
    agent_key: typeof value.agent_key === 'string' ? value.agent_key : undefined,
    table_count: typeof value.table_count === 'number' ? value.table_count : undefined,
    relationship_count: typeof value.relationship_count === 'number' ? value.relationship_count : undefined,
    fallback: typeof value.fallback === 'string' ? value.fallback : undefined,
    error: typeof value.error === 'string' ? value.error : undefined,
  }
  return attempt
}

const toTemplateMetadata = (value: unknown): TemplateGenerationMetadata | undefined => {
  if (!isRecord(value)) return undefined
  const metadata: TemplateGenerationMetadata = {
    provider: typeof value.provider === 'string' ? value.provider : undefined,
    model: typeof value.model === 'string' ? value.model : undefined,
    source: typeof value.source === 'string' ? value.source : undefined,
    used_llm: typeof value.used_llm === 'boolean' ? value.used_llm : undefined,
    fallback_reason:
      typeof value.fallback_reason === 'string'
        ? value.fallback_reason
        : value.fallback_reason === null
          ? null
          : undefined,
  }

  return Object.values(metadata).some((v) => v !== undefined) ? metadata : undefined
}

const toSqlGenerationDetails = (value: unknown): SqlGenerationDetails | undefined => {
  if (!isRecord(value)) return undefined

  const mode = toSqlModeEnum(value.mode)
  const source = typeof value.source === 'string' ? value.source : undefined
  const agentKey = typeof value.agent_key === 'string' ? value.agent_key : undefined
  const sqlPreview = typeof value.sql_preview === 'string' ? value.sql_preview : undefined
  const advantages = toStringArray(value.advantages)
  const reason = typeof value.reason === 'string' ? value.reason : undefined
  const fallbackTo = typeof value.fallback_to === 'string' ? value.fallback_to : undefined
  const templateMetadata = toTemplateMetadata(value.template_metadata)

  const attemptsRaw = Array.isArray(value.attempts) ? value.attempts : []
  const attempts = attemptsRaw
    .map(toSqlGenerationAttempt)
    .filter(
      (attempt): attempt is NonNullable<ReturnType<typeof toSqlGenerationAttempt>> =>
        attempt !== null && Object.values(attempt).some((v) => v !== undefined)
    )

  const details: SqlGenerationDetails = {}
  if (mode) details.mode = mode
  if (source) details.source = source
  if (agentKey) details.agent_key = agentKey
  if (sqlPreview) details.sql_preview = sqlPreview
  if (advantages.length) details.advantages = advantages
  if (reason) details.reason = reason
  if (fallbackTo) details.fallback_to = fallbackTo
  if (templateMetadata) details.template_metadata = templateMetadata
  if (attempts.length) details.attempts = attempts

  return Object.keys(details).length > 0 ? details : undefined
}

const toExecutionTrace = (value: unknown): ExecutionTraceItem[] | undefined => {
  if (!Array.isArray(value)) return undefined

  const items = value
    .map((entry) => {
      if (!isRecord(entry)) return null
      const phase = typeof entry.phase === 'string' ? entry.phase : 'unknown'
      const trace: ExecutionTraceItem = { phase }

      const agentMeta = toAgentMetadata(entry.agent)
      if (agentMeta) trace.agent = agentMeta
      if (typeof entry.reason === 'string') trace.reason = entry.reason
      if (Array.isArray(entry.tools)) {
        const tools = toStringArray(entry.tools)
        if (tools.length) trace.tools = tools
      }
      if (typeof entry.order === 'number') trace.order = entry.order
      if (typeof entry.tool_name === 'string') trace.tool_name = entry.tool_name
      if (isRecord(entry.args)) trace.args = entry.args
      if (typeof entry.response_preview === 'string') trace.response_preview = entry.response_preview
      if (isRecord(entry.response_summary)) trace.response_summary = entry.response_summary
      if (typeof entry.mode === 'string') trace.mode = entry.mode
      if (typeof entry.sql_preview === 'string') trace.sql_preview = entry.sql_preview
      if (typeof entry.executor === 'string') trace.executor = entry.executor
      if (typeof entry.row_count === 'number') trace.row_count = entry.row_count
      if (typeof entry.status === 'string') trace.status = entry.status
      if (typeof entry.error === 'string') trace.error = entry.error
      if (typeof entry.source === 'string') trace.source = entry.source
      if (typeof entry.character_count === 'number') trace.character_count = entry.character_count
      if (typeof entry.chart_type === 'string') trace.chart_type = entry.chart_type
      if (typeof entry.table_count === 'number') trace.table_count = entry.table_count
      if (typeof entry.relationship_count === 'number') trace.relationship_count = entry.relationship_count

      return trace
    })
    .filter((item): item is ExecutionTraceItem => item !== null)

  return items.length > 0 ? items : undefined
}

const toAgentSummary = (value: unknown): AgentSummary | null => {
  if (!isRecord(value)) return null
  const metadata = toAgentMetadata(value)
  if (!metadata) return null
  const active =
    typeof value.active === 'boolean'
      ? value.active
      : typeof value.active === 'string'
        ? value.active.toLowerCase() === 'true'
        : true

  return {
    ...metadata,
    active,
  }
}

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: '/api',
  timeout: 30000, // 30초 타임아웃
  headers: {
    'Content-Type': 'application/json',
  },
})

const normalizeChartType = (chart: string | undefined): ChartType => {
  switch ((chart || '').toLowerCase()) {
    case 'bar':
    case 'bar_chart':
      return 'bar'
    case 'line':
    case 'line_chart':
      return 'line'
    case 'pie':
    case 'pie_chart':
      return 'pie'
    default:
      return 'table'
  }
}

const normalizeGeneralResponse = (payload: unknown): QueryResponse => {
  if (!isRecord(payload)) {
    return {
      response: '분석 결과가 준비되었습니다.',
      data: [],
      chart_type: 'table'
    }
  }

  const agentMetadata = toAgentMetadata(payload.agent_metadata)
  const executionTrace = toExecutionTrace(payload.execution_trace)
  const sqlDetails = toSqlGenerationDetails(payload.sql_generation_details)
  const sqlMode = toSqlMode(payload.sql_mode)
  const adkAgent = typeof payload.adk_agent === 'string' ? payload.adk_agent : undefined
  const adkModel = typeof payload.adk_model === 'string' ? payload.adk_model : undefined

  const chartType = normalizeChartType(
    typeof payload.chart_suggestion === 'string' ? payload.chart_suggestion : undefined
  )

  const data = toRecordArray(payload.query_result)

  return {
    response: typeof payload.response === 'string' ? payload.response : '분석 결과가 준비되었습니다.',
    data,
    chart_type: chartType,
    sql: typeof payload.sql_query === 'string' ? payload.sql_query : undefined,
    execution_time: typeof payload.execution_time === 'number' ? payload.execution_time : undefined,
    analysis_steps: Array.isArray(payload.analysis_steps)
      ? payload.analysis_steps.filter((step): step is string => typeof step === 'string')
      : undefined,
    sql_mode: sqlMode,
    adk_agent: adkAgent,
    adk_model: adkModel,
    agent_metadata: agentMetadata,
    execution_trace: executionTrace,
    sql_generation_details: sqlDetails,
    raw: payload
  }
}

const normalizeSaaSResponse = (payload: unknown): QueryResponse => {
  if (!isRecord(payload)) {
    return {
      response: '분석 결과가 준비되었습니다.',
      data: [],
      chart_type: 'table'
    }
  }

  const chartType = normalizeChartType(
    typeof payload.chart_type === 'string' ? payload.chart_type : undefined
  )

  const data = toRecordArray(payload.data)
  const rawResult = isRecord(payload.raw_result) ? payload.raw_result : undefined
  const metrics = isRecord(payload.metrics) ? payload.metrics : undefined

  return {
    response: typeof payload.response === 'string' ? payload.response : '분석 결과가 준비되었습니다.',
    data,
    chart_type: chartType,
    execution_time: typeof rawResult?.metadata === 'object' && rawResult?.metadata !== null
      && typeof (rawResult.metadata as Record<string, unknown>).execution_time === 'number'
      ? (rawResult.metadata as Record<string, unknown>).execution_time as number
      : undefined,
    metrics,
    recommendations: Array.isArray(payload.recommendations)
      ? payload.recommendations.filter((item): item is string => typeof item === 'string')
      : undefined,
    analysis_steps: Array.isArray(payload.analysis_steps)
      ? payload.analysis_steps.filter((step): step is string => typeof step === 'string')
      : undefined,
    raw: payload
  }
}

const normalizeUnifiedResponse = (payload: unknown): UnifiedQueryResponse => {
  if (!isRecord(payload)) {
    throw new Error('Invalid unified query response')
  }

  return {
    response: typeof payload.response === 'string' ? payload.response : '',
    sql_query: typeof payload.sql_query === 'string' ? payload.sql_query : undefined,
    query_result: toRecordArray(payload.query_result),
    chart_suggestion: typeof payload.chart_suggestion === 'string' ? payload.chart_suggestion : undefined,
    execution_time: typeof payload.execution_time === 'number' ? payload.execution_time : undefined,
    error: typeof payload.error === 'string' ? payload.error : undefined,
    domain: typeof payload.domain === 'string' ? payload.domain : 'general',
    domain_confidence: typeof payload.domain_confidence === 'number' ? payload.domain_confidence : 0,
    domain_reasoning: typeof payload.domain_reasoning === 'string' ? payload.domain_reasoning : '',
    execution_mode: typeof payload.execution_mode === 'string' ? payload.execution_mode : 'auto',
    execution_reasoning: typeof payload.execution_reasoning === 'string' ? payload.execution_reasoning : '',
    process_trace: isRecord(payload.process_trace) ? payload.process_trace as any : {
      domain_classification: { domain: '', confidence: 0, matched_keywords: [], suggested_tables: [] },
      domain_context: { domain_name: '', tables: [], metrics: [] },
      execution_mode: { mode: '', reasoning: '', tools: [] },
      agent_execution: { agent_name: '', model: '', tool_calls: [], response_length: 0 }
    },
    analysis_steps: Array.isArray(payload.analysis_steps)
      ? payload.analysis_steps.filter((step): step is string => typeof step === 'string')
      : [],
    adk_agent: typeof payload.adk_agent === 'string' ? payload.adk_agent : undefined,
    adk_model: typeof payload.adk_model === 'string' ? payload.adk_model : undefined,
  }
}

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    // 요청 시작 시간 기록
    config.metadata = { startTime: Date.now() }

    // 요청 로깅
    logger.apiRequest(
      config.method?.toUpperCase() || 'GET',
      config.url || '',
      config.data
    )

    return config
  },
  (error) => {
    logger.error('API request setup failed', error)
    return Promise.reject(error)
  }
)

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    // 응답 시간 계산
    const duration = Date.now() - (response.config.metadata?.startTime || Date.now())

    // 응답 로깅
    logger.apiResponse(
      response.config.method?.toUpperCase() || 'GET',
      response.config.url || '',
      response.status,
      duration,
      response.data
    )

    return response
  },
  (error) => {
    // 에러 로깅
    const method = error.config?.method?.toUpperCase() || 'GET'
    const url = error.config?.url || ''

    logger.apiError(method, url, error)

    // 에러 메시지 정규화
    const errorMessage = error.response?.data?.detail ||
                        error.response?.data?.message ||
                        error.message ||
                        '알 수 없는 오류가 발생했습니다.'

    return Promise.reject(new Error(errorMessage))
  }
)

export const apiService = {
  // 헬스 체크
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await api.get('/system/health')
    return response.data
  },

  // 쿼리 처리
  async processQuery(request: QueryRequest): Promise<QueryResponse> {
    const { data } = await api.post('/chat/query', request)
    return normalizeGeneralResponse(data)
  },

  // SaaS 분석 쿼리 처리
  async processSaaSQuery(request: SaaSQueryRequest): Promise<QueryResponse> {
    const { data } = await api.post('/chat/saas-query', request)
    return normalizeSaaSResponse(data)
  },

  // 통합 쿼리 처리 (4-Layer Architecture)
  async processUnifiedQuery(request: UnifiedQueryRequest): Promise<UnifiedQueryResponse> {
    const { data } = await api.post('/chat/unified-query', request)
    return normalizeUnifiedResponse(data)
  },

  // SaaS 예시 질문 가져오기
  async getSaaSExampleQueries(): Promise<string[]> {
    const { data } = await api.get('/chat/saas-example-queries')
    return Array.isArray(data?.queries) ? data.queries : []
  },

  // 데이터 소스 정보 조회
  async getDataSources(): Promise<DataSource[]> {
    const { data } = await api.get('/data/sources')
    if (Array.isArray(data)) {
      return data.filter((item): item is DataSource =>
        isRecord(item) &&
        typeof item.name === 'string' &&
        typeof item.display_name === 'string' &&
        typeof item.description === 'string' &&
        typeof item.table_count === 'number'
      )
    }
    return []
  },

  // 특정 테이블 스키마 조회
  async getTableSchema(tableName: string): Promise<Record<string, unknown>> {
    const { data } = await api.get(`/data/tables/${tableName}/schema`)
    return data
  },

  // 시스템 상태 조회
  async getSystemStatus(): Promise<SystemStatus> {
    const { data } = await api.get('/system/health')
    const checks = isRecord(data?.checks) ? data.checks : undefined
    const bigqueryStatus = isRecord(checks?.bigquery) ? checks.bigquery : undefined
    const aiStatus = isRecord(checks?.ai) ? checks.ai : undefined
    const sqlEngine = isRecord(checks?.sql_engine) ? checks.sql_engine : undefined
    const sqlComponents = Array.isArray(sqlEngine?.components)
      ? (sqlEngine.components as unknown[]).filter((component): component is string => typeof component === 'string')
      : undefined
    return {
      bigquery_connected: bigqueryStatus?.status === 'healthy',
      openai_configured: true,
      last_health_check: typeof data?.timestamp === 'string' ? data.timestamp : '',
      version: typeof data?.version === 'string' ? data.version : '1.0.0',
      model_provider: typeof aiStatus?.provider === 'string' ? aiStatus.provider : undefined,
      model_name: typeof aiStatus?.model === 'string' ? aiStatus.model : undefined,
      sql_generation: typeof sqlEngine?.mode === 'string' ? sqlEngine.mode : undefined,
      sql_components: sqlComponents,
      sql_description: typeof sqlEngine?.description === 'string' ? sqlEngine.description : undefined
    }
  },

  // 쿼리 히스토리 조회
  async getQueryHistory(limit: number = 10): Promise<Record<string, unknown>[]> {
    const { data } = await api.get(`/chat/history/demo-user?limit=${limit}`)
    return Array.isArray(data?.messages) ? data.messages.filter(isRecord) : []
  },

  // 사용자 피드백 전송
  async sendFeedback(payload: { message_id: string; feedback_type: 'like' | 'dislike'; comment?: string; user_id?: string }): Promise<void> {
    await api.post('/chat/feedback', {
      query_id: payload.message_id,
      feedback_type: payload.feedback_type,
      comment: payload.comment,
      user_id: payload.user_id
    })
  },

  // 예시 쿼리 조회
  async getExampleQueries(): Promise<string[]> {
    const { data } = await api.get('/chat/examples')
    if (!Array.isArray(data)) return []
    return data
      .map((item) => (isRecord(item) && typeof item.question === 'string' ? item.question : null))
      .filter((value): value is string => value !== null)
  },

  async getAgents(): Promise<AgentSummary[]> {
    const { data } = await api.get('/chat/agents')
    if (!Array.isArray(data)) return []
    return data
      .map(toAgentSummary)
      .filter((item): item is AgentSummary => item !== null)
  },

  // SQL 쿼리 직접 실행 (개발/디버깅 용도)
  async executeSQL(sql: string): Promise<Record<string, unknown>[]> {
    const { data } = await api.post('/data/execute', { sql_query: sql })
    return Array.isArray(data) ? data.filter(isRecord) : []
  },

  // SSE 스트리밍
  streamQuery(request: QueryRequest, onEvent: SSEEventHandler): () => void {
    return streamQuery(request, onEvent)
  },

  // 파일 업로드
  async uploadFile(file: File): Promise<{ file_path: string; filename: string }> {
    const formData = new FormData()
    formData.append('file', file)
    
    // axios의 Content-Type 자동 설정에 맡기거나 명시적으로 multipart/form-data 헤더를 설정
    const { data } = await api.post('/chat/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 파일 업로드는 시간이 걸릴 수 있음
    })
    return data
  }
}

// 에러 핸들링 유틸리티
export const handleApiError = (error: unknown): string => {
  if (isRecord(error) && error.response) {
    const response = error.response as Record<string, unknown>
    // 서버에서 응답을 받았지만 에러 상태 코드
    const status = typeof response.status === 'number' ? response.status : undefined
    const data = isRecord(response.data) ? response.data : undefined
    const message = (typeof data?.detail === 'string' ? data.detail : undefined) ??
      (typeof data?.message === 'string' ? data.message : undefined)

    switch (status) {
      case 400:
        return `잘못된 요청입니다: ${message}`
      case 401:
        return '인증이 필요합니다.'
      case 403:
        return '접근 권한이 없습니다.'
      case 404:
        return '요청한 리소스를 찾을 수 없습니다.'
      case 429:
        return '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.'
      case 500:
        return '서버 내부 오류가 발생했습니다.'
      case 503:
        return '서비스를 일시적으로 사용할 수 없습니다.'
      default:
        return message || (status ? `서버 오류 (${status})` : '서버 오류가 발생했습니다.')
    }
  } else if (isRecord(error) && 'request' in error) {
    // 요청은 보냈지만 응답을 받지 못함
    return '서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.'
  } else {
    // 요청 설정 중 오류 발생
    if (isRecord(error) && typeof error.message === 'string') {
      return error.message
    }
    return '알 수 없는 오류가 발생했습니다.'
  }
}

// ============================================================================
// SSE (Server-Sent Events) 스트리밍 타입 정의
// ============================================================================

export interface SSEEvent {
  event: string
  data: unknown
}

export type SSEEventHandler = (event: SSEEvent) => void

// ============================================================================
// SSE 스트리밍 API
// ============================================================================

export function streamQuery(
  request: QueryRequest,
  onEvent: SSEEventHandler
): () => void {
  /**
   * SSE를 사용하여 실시간 ADK 이벤트를 스트리밍합니다.
   *
   * 이벤트 타입:
   * - start: 스트리밍 시작
   * - agent_info: 에이전트 정보
   * - thinking: AI 사고 과정 (텍스트 응답)
   * - tool_call: 도구 호출
   * - sql: SQL 쿼리 생성
   * - result: 쿼리 결과
   * - response: 최종 응답
   * - done: 완료
   * - error: 에러
   *
   * @param request 쿼리 요청
   * @param onEvent 이벤트 핸들러
   * @returns 연결 종료 함수
   */

  const url = new URL('/api/chat/query-stream', window.location.origin)

  // EventSource는 GET만 지원하므로 fetch + ReadableStream 사용
  const controller = new AbortController()

  logger.info('[SSE] 연결 시작:', url.toString())
  logger.info('[SSE] 요청 데이터:', request)

  fetch(url.toString(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
    signal: controller.signal,
  })
    .then(async (response) => {
      logger.info('[SSE] 응답 수신:', response.status, response.statusText)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      if (!response.body) {
        throw new Error('No response body')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let eventCount = 0

      logger.info('[SSE] ReadableStream 읽기 시작')

      try {
        while (true) {
          const { done, value } = await reader.read()

          if (done) {
            logger.info('[SSE] 스트림 종료 (done=true)')
            break
          }

          // 새로운 데이터를 버퍼에 추가
          const chunk = decoder.decode(value, { stream: true })
          logger.debug(`[SSE] 청크 수신: ${chunk.length}바이트`)
          buffer += chunk

          // SSE 메시지 파싱 (event: xxx\ndata: yyy\n\n 형식)
          const messages = buffer.split('\n\n')
          buffer = messages.pop() || '' // 마지막 불완전한 메시지는 버퍼에 유지

          for (const message of messages) {
            if (!message.trim()) continue

            const lines = message.split('\n')
            let event = 'message'
            let data = ''

            for (const line of lines) {
              if (line.startsWith('event: ')) {
                event = line.slice(7).trim()
              } else if (line.startsWith('data: ')) {
                data = line.slice(6).trim()
              }
            }

            if (data) {
              try {
                const parsed = JSON.parse(data)
                eventCount++
                logger.info(`[SSE] 이벤트 #${eventCount}: ${event}`, parsed)
                onEvent({ event, data: parsed })
              } catch (e) {
                logger.error('SSE 파싱 에러', e)
                onEvent({ event: 'error', data: { error: 'Failed to parse SSE data' } })
              }
            }
          }
        }

        logger.info(`[SSE] 스트림 완료 (총 ${eventCount}개 이벤트)`)
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          logger.error('SSE 스트림 에러', error)
          onEvent({ event: 'error', data: { error: error.message } })
        }
      }
    })
    .catch((error) => {
      if (error.name !== 'AbortError') {
        logger.error('SSE 연결 에러', error)
        onEvent({ event: 'error', data: { error: error.message } })
      }
    })

  // 연결 종료 함수 반환
  return () => {
    controller.abort()
  }
}

export default api
