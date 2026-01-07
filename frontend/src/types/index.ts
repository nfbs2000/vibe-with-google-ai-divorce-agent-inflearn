// API 요청/응답 타입
export interface QueryRequest {
  query: string
  user_id?: string
  session_id?: string
  conversation_history?: Array<{
    role: 'user' | 'assistant'
    content: string
    timestamp?: string
  }>
  dry_run?: boolean
  sql_mode?: 'template' | 'schema_aware'  // SQL 생성 방식 선택
  agent_type?: 'sql' | 'conversational'   // 실행할 에이전트 유형
  files?: string[]                        // 첨부 파일 경로 리스트
}

export interface SaaSQueryRequest {
  message: string
  user_id?: string
  use_api?: boolean
  conversation_history?: Array<{
    role: 'user' | 'assistant'
    content: string
    timestamp?: string
  }>
}

export type ChartType = 'bar' | 'line' | 'pie' | 'table' | 'area' | 'scatter' | 'gauge'

export type SqlGenerationMode = 'adk' | 'schema_aware' | 'template' | 'unknown'

export interface AgentMetadata {
  key: string
  display_name: string
  description: string
  focus: string
  strengths?: string[]
  keywords?: string[]
  model?: string
}

export interface SqlGenerationAttempt {
  mode?: string
  status?: string
  agent_key?: string
  table_count?: number
  relationship_count?: number
  fallback?: string
  error?: string
}

export interface TemplateGenerationMetadata {
  provider?: string
  model?: string
  source?: string
  used_llm?: boolean
  fallback_reason?: string | null
}

export interface SqlGenerationDetails {
  mode?: SqlGenerationMode
  source?: string
  agent_key?: string
  sql_preview?: string
  advantages?: string[]
  reason?: string
  fallback_to?: string
  template_metadata?: TemplateGenerationMetadata
  attempts?: SqlGenerationAttempt[]
}

export type ExecutionTracePhase =
  | 'agent_selection'
  | 'adk_tool_call'
  | 'schema_aware_prepare'
  | 'sql_generated'
  | 'query_execution'
  | 'result_interpretation'
  | 'chart_suggestion'
  | 'agent_response'
  | string

export interface ReasoningStep {
  step_number: number
  phase: string
  thought: string
  confidence: number
  timestamp: string
  metadata?: Record<string, unknown>
}

export interface ReasoningDetail {
  total_steps: number
  steps: ReasoningStep[]
}

export interface ExecutionTraceItem {
  phase: ExecutionTracePhase
  agent?: AgentMetadata
  reason?: string
  tools?: string[]
  order?: number
  tool_name?: string
  args?: Record<string, unknown>
  response_preview?: string
  response_summary?: Record<string, unknown>
  mode?: string
  sql_preview?: string
  executor?: string
  row_count?: number | null
  status?: string
  error?: string
  source?: string
  character_count?: number
  chart_type?: string
  table_count?: number
  relationship_count?: number
}

export interface QueryResponse {
  response: string
  data: Record<string, unknown>[]
  chart_type: ChartType
  sql?: string
  execution_time?: number
  metrics?: Record<string, unknown>
  recommendations?: string[]
  raw?: Record<string, unknown>
  analysis_steps?: string[]
  reasoning_detail?: ReasoningDetail  // 구조화된 추론 상세 정보
  reasoning_formatted?: string  // 포맷팅된 추론 텍스트
  sql_mode?: 'template' | 'schema_aware' | 'adk' | 'conversational'  // 실제 사용된 SQL 생성 방식
  adk_agent?: string  // Google ADK Agent 이름
  adk_model?: string  // ADK Agent가 사용한 모델
  agent_metadata?: AgentMetadata
  execution_trace?: ExecutionTraceItem[]
  sql_generation_details?: SqlGenerationDetails
  // 4-Layer 아키텍처 정보
  domain?: string  // 분류된 도메인 (security, conversion, marketing, general)
  domain_confidence?: number  // 도메인 분류 신뢰도 (0.0-1.0)
  execution_mode?: string  // 실행 모드 (sql, conversational, auto)
}

// 메시지 타입
export interface Message {
  id: string
  sender: 'user' | 'assistant' | 'error'
  content: string
  timestamp: Date
  queryResult?: QueryResponse
  isError?: boolean
}

// 데이터 소스 타입
export interface DataSource {
  name: string
  display_name: string
  description: string
  table_count: number
  total_rows?: number
  last_updated?: string
  status: 'active' | 'inactive' | 'error'
}

export interface TableSchema {
  name: string
  type: string
  mode: 'NULLABLE' | 'REQUIRED' | 'REPEATED'
  description?: string
}

// 차트 설정 타입
export interface ChartConfig {
  type: ChartType
  title?: string
  xAxis?: string
  yAxis?: string
  colors?: string[]
}

// API 에러 타입
export interface ApiError {
  message: string
  code?: string
  details?: unknown
}

// 사용자 피드백 타입
export interface UserFeedback {
  messageId: string
  type: 'like' | 'dislike'
  comment?: string
  timestamp: Date
}

// 쿼리 히스토리 타입
export interface QueryHistory {
  id: string
  query: string
  response: QueryResponse
  timestamp: Date
  feedback?: UserFeedback
}

// 시스템 상태 타입
export interface SystemStatus {
  bigquery_connected: boolean
  openai_configured: boolean
  last_health_check: string
  version: string
  model_provider?: string
  model_name?: string
  sql_generation?: string
  sql_components?: string[]
  sql_description?: string
}

export interface AgentSummary extends AgentMetadata {
  active: boolean
}

// ========================================
// Unified Architecture Types
// ========================================

export type Domain = 'security' | 'conversion' | 'marketing' | 'general' | 'alyac_family' | 'divorce_case'
export type ExecutionMode = 'sql' | 'conversational' | 'auto'
export type StepStatus = 'pending' | 'in_progress' | 'completed' | 'error'

// Domain Classification
export interface DomainClassification {
  domain: Domain
  confidence: number
  matched_keywords: string[]
  suggested_tables: string[]
  reasoning: string
}

export interface AlternativeDomain {
  domain: Domain
  confidence: number
}

// Process Step for UnifiedProcessFlow
export interface ProcessStep {
  layer: number
  name: string
  status: StepStatus
  data?: Record<string, unknown>
  details?: string[]
  timestamp?: string
}

// Process Trace (4-layer architecture trace)
export interface ProcessTrace {
  domain_classification: {
    domain: string
    confidence: number
    matched_keywords: string[]
    suggested_tables: string[]
  }
  domain_context: {
    domain_name: string
    tables: string[]
    metrics: string[]
  }
  execution_mode: {
    mode: string
    reasoning: string
    tools: string[]
  }
  agent_execution: {
    agent_name: string
    model: string
    tool_calls: unknown[]
    response_length: number
  }
}

// Unified Query Request
export interface UnifiedQueryRequest {
  message: string
  execution_mode?: ExecutionMode
  conversation_history?: Array<{
    role: 'user' | 'assistant'
    content: string
    timestamp?: string
  }>
  user_id?: string
  session_id?: string
}

// Unified Query Response
export interface UnifiedQueryResponse {
  // 기본 응답 데이터
  response: string
  sql_query?: string
  query_result?: Record<string, unknown>[]
  chart_suggestion?: string
  execution_time?: number
  error?: string

  // 도메인 정보
  domain: string
  domain_confidence: number
  domain_reasoning: string

  // 실행 방식 정보
  execution_mode: string
  execution_reasoning: string

  // 프로세스 추적
  process_trace: ProcessTrace
  analysis_steps: string[]

  // 에이전트 정보
  adk_agent?: string
  adk_model?: string
  
  // 실행 추적
  execution_trace?: ExecutionTraceItem[]
}
