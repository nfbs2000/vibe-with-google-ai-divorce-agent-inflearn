"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { LucideIcon } from "lucide-react"
import {
  Activity,
  AlertTriangle,
  Bot,
  Database,
  Globe,
  Info,
  Network,
  Play,
  ShieldCheck,
  TrendingUp,
  Wand2,
  Wrench,
  Lightbulb,
  Scale,
  User,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea, ScrollViewport } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

type StatusTone = "info" | "pending" | "success" | "error"

interface LiveStatus {
  tone: StatusTone
  message: string
}

interface StreamPayload {
  _meta?: { sequence?: number; timestamp?: number }
  [key: string]: unknown
}

interface StreamEvent {
  sequence: number
  name: string
  payload: StreamPayload
  timestamp: number
}

type ConversationActor = "user" | "agent" | "tool" | "remote" | "system" | "unknown"

interface ConversationEntry {
  id: string
  actor: ConversationActor
  title: string
  body: string
  timestamp: number
  badges: string[]
  raw: StreamPayload
}

const MAX_BODY_LENGTH = 600

type TemplateCategory = "security" | "kpi" | "product" | "governance" | "other"
type TemplateFilterValue = "all" | TemplateCategory

const TEMPLATE_CATEGORY_ORDER: TemplateCategory[] = ["security", "kpi", "product", "governance", "other"]

const TEMPLATE_CATEGORY_CONFIG: Record<TemplateCategory, { label: string; icon: LucideIcon }> = {
  security: { label: "보안", icon: ShieldCheck },
  kpi: { label: "운영 KPI", icon: TrendingUp },
  product: { label: "제품 인사이트", icon: Lightbulb },
  governance: { label: "거버넌스", icon: Scale },
  other: { label: "기타", icon: Wrench },
}

const TEMPLATE_CATEGORY_MAP: Record<string, TemplateCategory> = {
  risk_app_actions: "security",
  anti_phishing_packages: "security",
  security_permission_anomalies: "security",
  security_risk_level_trend: "security",
  engine_compare_summary: "security",
  os_usage_daily: "kpi",
  engagement_daily_overview: "kpi",
  retention_cohort_daily: "kpi",
  version_performance_summary: "kpi",
}

const TEMPLATE_FILTER_OPTIONS: Array<{ value: TemplateFilterValue; label: string; icon: LucideIcon }> = [
  { value: "all", label: "전체", icon: Globe },
  ...TEMPLATE_CATEGORY_ORDER.map((category) => ({
    value: category,
    label: TEMPLATE_CATEGORY_CONFIG[category].label,
    icon: TEMPLATE_CATEGORY_CONFIG[category].icon,
  })),
]

function getTemplateCategory(id: string): TemplateCategory {
  return TEMPLATE_CATEGORY_MAP[id] ?? "other"
}

function pickDeepString(source: unknown, paths: string[][]): string | null {
  for (const path of paths) {
    let current: unknown = source
    for (const key of path) {
      if (current && typeof current === "object" && key in current) {
        current = (current as Record<string, unknown>)[key]
      } else {
        current = undefined
        break
      }
    }
    if (typeof current === "string" && current.trim()) {
      return current.trim()
    }
  }
  return null
}

function extractContentText(payload: StreamPayload): string | null {
  const parts: string[] = []
  const content = payload.content as unknown
  if (Array.isArray((content as { parts?: unknown[] })?.parts)) {
    for (const part of (content as { parts: unknown[] }).parts) {
      if (part && typeof part === "object" && "text" in part) {
        const textValue = (part as Record<string, unknown>).text
        if (typeof textValue === "string" && textValue.trim()) {
          parts.push(textValue.trim())
        }
      }
    }
  } else if (typeof content === "string" && content.trim()) {
    parts.push(content.trim())
  }

  const directTexts = ["message", "text", "response", "output", "result"]
  for (const key of directTexts) {
    const value = payload[key]
    if (typeof value === "string" && value.trim()) {
      parts.push(value.trim())
    }
  }

  if (parts.length > 0) {
    return parts.join("\n\n")
  }
  return null
}

function stringifyFallback(payload: StreamPayload): string {
  try {
    const raw = JSON.stringify(payload, null, 2)
    if (raw.length > MAX_BODY_LENGTH) {
      return `${raw.slice(0, MAX_BODY_LENGTH)}…`
    }
    return raw
  } catch (error) {
    console.warn("[ADK] payload stringify 실패", error)
    return "(payload 미리보기 생성 실패)"
  }
}

function deriveConversationEntry(event: StreamEvent): ConversationEntry | null {
  if (event.name !== "adk.event") return null
  const payload = event.payload

  const author = typeof payload.author === "string" ? payload.author.toLowerCase() : undefined

  const remoteAgent =
    pickDeepString(payload, [
      ["remoteAgent"],
      ["remote_agent"],
      ["remoteAgentId"],
      ["remote_agent_id"],
      ["agentName"],
      ["agent_id"],
      ["routing", "agent"],
      ["a2a", "agentName"],
      ["target", "agentId"],
      ["targetAgent"],
    ]) ?? undefined

  const toolName =
    pickDeepString(payload, [
      ["toolName"],
      ["tool_name"],
      ["toolId"],
      ["tool_id"],
      ["tool", "name"],
      ["toolInvocation", "toolName"],
      ["toolCall", "name"],
      ["action", "toolName"],
      ["action", "tool"],
      ["metadata", "tool"],
    ]) ?? undefined

  let actor: ConversationActor = "unknown"
  let title = event.name

  if (author === "user") {
    actor = "user"
    title = "사용자 프롬프트"
  } else if (author === "agent" || author === "assistant") {
    actor = "agent"
    title = "에이전트 응답"
  } else if (author === "tool") {
    actor = "tool"
    title = toolName ? `툴 호출 · ${toolName}` : "툴 호출"
  } else if (author === "system") {
    actor = "system"
    title = "시스템 알림"
  } else if (remoteAgent) {
    actor = "remote"
    title = `원격 에이전트 · ${remoteAgent}`
  } else if (toolName) {
    actor = "tool"
    title = `툴 호출 · ${toolName}`
  }

  if (actor === "unknown" && remoteAgent) {
    actor = "remote"
    title = `원격 에이전트 · ${remoteAgent}`
  }
  if (actor === "unknown" && toolName) {
    actor = "tool"
    title = `툴 호출 · ${toolName}`
  }

  const text = extractContentText(payload)
  const body = text && text.trim() ? text.trim() : stringifyFallback(payload)

  const badges: string[] = []
  if (payload.turnComplete) badges.push("turn-complete")
  const status = pickDeepString(payload, [["status"], ["state"], ["phase"]])
  if (status) badges.push(status)
  if (remoteAgent && !badges.includes("remote")) badges.push("remote")
  if (toolName && !badges.includes("tool")) badges.push("tool")

  return {
    id: `${event.sequence}`,
    actor,
    title,
    body,
    timestamp: event.timestamp,
    badges,
    raw: payload,
  }
}

const actorConfig: Record<
  ConversationActor,
  { label: string; icon: React.ComponentType<{ className?: string }>; cardClass: string; badgeClass: string }
> = {
  user: {
    label: "사용자",
    icon: User,
    cardClass: "border-emerald-400/40 bg-emerald-500/5",
    badgeClass: "border-emerald-400/60 text-emerald-200",
  },
  agent: {
    label: "에이전트",
    icon: Bot,
    cardClass: "border-emerald-400/50 bg-emerald-500/10",
    badgeClass: "border-emerald-400/70 text-emerald-100",
  },
  tool: {
    label: "툴",
    icon: Wrench,
    cardClass: "border-emerald-400/30 bg-emerald-500/5",
    badgeClass: "border-emerald-400/50 text-emerald-200",
  },
  remote: {
    label: "원격 에이전트",
    icon: Network,
    cardClass: "border-emerald-400/35 bg-emerald-500/8",
    badgeClass: "border-emerald-400/60 text-emerald-100",
  },
  system: {
    label: "시스템",
    icon: Info,
    cardClass: "border-slate-400/40 bg-slate-500/5",
    badgeClass: "border-slate-400/60 text-slate-100",
  },
  unknown: {
    label: "기타",
    icon: Activity,
    cardClass: "border-emerald-500/20 bg-slate-900/60",
    badgeClass: "border-emerald-500/40 text-emerald-300",
  },
}

interface TemplateMeta {
  id: string
  label: string
  description?: string
  required_params?: string[]
  defaults?: Record<string, string>
  category?: TemplateCategory
}

interface RenderedTemplate {
  template_id: string
  sql: string
  params: Record<string, unknown>
  dry_run?: {
    total_bytes_processed?: number
    schema?: unknown
  }
  warnings?: string[]
}

type CategorizedTemplate = TemplateMeta & { category: TemplateCategory }

const DEFAULT_PROMPT = "최근 7일간 악성 앱 탐지 이벤트 추이를 알려줘."
const DEFAULT_STATUS: LiveStatus = { tone: "info", message: "대기 중" }

export function InspectorView() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT)
  const [status, setStatus] = useState<LiveStatus>(DEFAULT_STATUS)
  const [runId, setRunId] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [events, setEvents] = useState<StreamEvent[]>([])

  const [templates, setTemplates] = useState<CategorizedTemplate[]>([])
  const [templateStatus, setTemplateStatus] = useState<LiveStatus>({ tone: "pending", message: "템플릿 로딩 중" })
  const [selectedTemplate, setSelectedTemplate] = useState<CategorizedTemplate | null>(null)
  const [templateParams, setTemplateParams] = useState<Record<string, string>>({})
  const [renderResult, setRenderResult] = useState<RenderedTemplate | null>(null)
  const [renderStatus, setRenderStatus] = useState<LiveStatus>({ tone: "info", message: "" })
  const [dryRun, setDryRun] = useState(false)
  const [templateFilter, setTemplateFilter] = useState<TemplateFilterValue>("all")

  const filteredTemplates = useMemo(() => {
    if (templateFilter === "all") return templates
    return templates.filter((template) => template.category === templateFilter)
  }, [templateFilter, templates])

  const sourceRef = useRef<EventSource | null>(null)

  const reset = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close()
      sourceRef.current = null
    }
    setEvents([])
    setRunId(null)
    setSessionId(null)
  }, [])

  useEffect(() => () => reset(), [reset])

  useEffect(() => {
    const controller = new AbortController()
    async function loadTemplates() {
      try {
        const response = await fetch("/api/templates", { signal: controller.signal })
        if (!response.ok) {
          throw new Error(`템플릿 목록을 불러오지 못했습니다 (${response.status})`)
        }
        const data = await response.json()
        const rawTemplates: TemplateMeta[] = data.templates ?? []
        const categorized: CategorizedTemplate[] = rawTemplates.map((template) => ({
          ...template,
          category: getTemplateCategory(template.id),
        }))
        setTemplates(categorized)
        if (categorized.length) {
          setTemplateStatus({ tone: "success", message: `${categorized.length}개 템플릿` })
        } else {
          setTemplateStatus({ tone: "info", message: "사용 가능한 템플릿이 없습니다." })
        }
      } catch (error) {
        if (controller.signal.aborted) return
        console.error("[ADK] 템플릿 로딩 실패", error)
        setTemplateStatus({
          tone: "error",
          message: error instanceof Error ? error.message : "템플릿 로딩 실패",
        })
      }
    }

    loadTemplates()
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (filteredTemplates.length === 0) {
      setSelectedTemplate(null)
      setTemplateParams({})
      return
    }
    if (!selectedTemplate || !filteredTemplates.some((template) => template.id === selectedTemplate.id)) {
      const next = filteredTemplates[0]
      setSelectedTemplate(next)
      const defaults = (next.defaults ?? {}) as Record<string, string>
      setTemplateParams(defaults)
    }
  }, [filteredTemplates, selectedTemplate])

  const sortedEvents = useMemo(() => [...events].sort((a, b) => a.sequence - b.sequence), [events])

  const conversationEntries = useMemo(
    () =>
      sortedEvents
        .map((event) => deriveConversationEntry(event))
        .filter((entry): entry is ConversationEntry => entry !== null),
    [sortedEvents],
  )

  const appendEvent = useCallback((name: string, data: string) => {
    try {
      const payload: StreamPayload = JSON.parse(data)
      const meta = payload._meta ?? {}
      const sequence = typeof meta.sequence === "number" ? meta.sequence : events.length + 1
      const timestamp = typeof meta.timestamp === "number" ? meta.timestamp : Date.now() / 1000
      setEvents((prev) => [
        ...prev,
        {
          sequence,
          name,
          payload,
          timestamp,
        },
      ])
    } catch (error) {
      console.warn("[ADK] 이벤트 파싱 실패", error)
    }
  }, [events.length])

  const connectStream = useCallback((id: string) => {
    if (sourceRef.current) {
      sourceRef.current.close()
    }
    const source = new EventSource(`/api/live/events?run_id=${encodeURIComponent(id)}`)
    sourceRef.current = source

    source.onopen = () => {
      setStatus({ tone: "pending", message: "라이브 스트림 연결됨" })
    }

    source.addEventListener("adk.event", (event) => {
      appendEvent("adk.event", (event as MessageEvent<string>).data)
    })

    source.addEventListener("run.status", (event) => {
      const data = (event as MessageEvent<string>).data
      appendEvent("run.status", data)
      try {
        const parsed = JSON.parse(data)
        const state = parsed?.status
        if (state === "completed") {
          setStatus({ tone: "success", message: "워크플로 완료" })
          source.close()
          sourceRef.current = null
        } else if (state === "error") {
          setStatus({ tone: "error", message: `오류: ${parsed?.error ?? "알 수 없음"}` })
          source.close()
          sourceRef.current = null
        }
      } catch (error) {
        console.warn("[ADK] 상태 파싱 실패", error)
      }
    })

    source.addEventListener("run.error", (event) => {
      appendEvent("run.error", (event as MessageEvent<string>).data)
      setStatus({ tone: "error", message: "워크플로 실행 중 오류" })
      source.close()
      sourceRef.current = null
    })

    source.addEventListener("keepalive", () => {
      /* heartbeat */
    })

    source.onerror = (error) => {
      console.error("[ADK] SSE 에러", error)
      setStatus({ tone: "error", message: "스트림 연결 오류" })
      source.close()
      sourceRef.current = null
    }
  }, [appendEvent])

  const startRun = useCallback(async () => {
    const trimmed = prompt.trim()
    if (!trimmed) {
      setStatus({ tone: "error", message: "프롬프트를 입력하세요." })
      return
    }

    setStatus({ tone: "pending", message: "실행 준비 중…" })
    reset()

    try {
      const response = await fetch("/api/live/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: trimmed }),
      })
      if (!response.ok) {
        const message = await response.text()
        throw new Error(message || `실행 요청 실패 (${response.status})`)
      }
      const data = (await response.json()) as { run_id: string; session_id: string }
      setRunId(data.run_id)
      setSessionId(data.session_id)
      setStatus({ tone: "pending", message: "라이브 스트림 연결 중…" })
      connectStream(data.run_id)
    } catch (error) {
      console.error("[ADK] 실행 실패", error)
      setStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "실행에 실패했습니다.",
      })
    }
  }, [connectStream, prompt, reset])

  const toneToClass: Record<StatusTone, string> = {
    info: "text-muted-foreground",
    pending: "text-primary",
    success: "text-green-400",
    error: "text-red-400",
  }

  const handleTemplateSelect = useCallback((templateId: string) => {
    const template = templates.find((tpl) => tpl.id === templateId) ?? null
    setSelectedTemplate(template)
    setRenderResult(null)
    if (template) {
      const defaults = (template.defaults ?? {}) as Record<string, string>
      setTemplateParams(defaults)
    } else {
      setTemplateParams({})
    }
  }, [templates])

  const handleParamChange = useCallback((key: string, value: string) => {
    setTemplateParams((prev) => ({ ...prev, [key]: value }))
  }, [])

  const renderTemplate = useCallback(async () => {
    if (!selectedTemplate) return
    setRenderResult(null)
    setRenderStatus({ tone: "pending", message: "템플릿 렌더링 중…" })
    try {
      const response = await fetch("/api/templates/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_id: selectedTemplate.id,
          params: templateParams,
          dry_run: dryRun,
        }),
      })
      if (!response.ok) {
        const message = await response.text()
        throw new Error(message || `렌더링 실패 (${response.status})`)
      }
      const data = (await response.json()) as RenderedTemplate
      setRenderResult(data)
      setRenderStatus({ tone: "success", message: "템플릿 렌더링 완료" })
    } catch (error) {
      console.error("[ADK] 템플릿 렌더링 실패", error)
      setRenderStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "템플릿 렌더링 실패",
      })
    }
  }, [dryRun, selectedTemplate, templateParams])

  const applySqlToPrompt = useCallback(() => {
    if (!renderResult?.sql) return
    setPrompt(renderResult.sql)
    setStatus({ tone: "info", message: "템플릿 SQL을 프롬프트에 적용했습니다." })
  }, [renderResult?.sql])

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-4 pb-12 pt-8">
      <header className="relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-slate-900/95 via-emerald-950/30 to-slate-900/95 p-8 shadow-xl backdrop-blur-sm">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(16,185,129,0.1),transparent_50%)]" />
        <div className="relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/30">
                <Database className="h-4 w-4 text-emerald-400" />
              </div>
              <Badge className="border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-300">
                Google ADK · Inspector
              </Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white md:text-4xl">
              BigQuery 워크플로 인스펙터
            </h1>
            <p className="max-w-2xl text-sm leading-relaxed text-gray-300 md:text-base">
              실시간 이벤트 스트림으로 BigQuery 에이전트의 실행 과정, 도구 호출, 결과를 상세하게 추적합니다.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-2.5 shadow-lg backdrop-blur-sm">
            <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
            <span className="text-sm font-medium text-emerald-300">ADK Runner Ready</span>
          </div>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[400px_minmax(0,1fr)]">
        <div className="space-y-5">
          <Card className="border-emerald-500/20 bg-gradient-to-br from-slate-900/90 to-slate-900/70 backdrop-blur-sm">
            <CardHeader className="space-y-3 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/20">
                  <Wand2 className="h-4.5 w-4.5 text-emerald-400" />
                </div>
                <CardTitle className="text-lg font-bold text-white">
                  BigQuery 템플릿
                </CardTitle>
              </div>
              <CardDescription className="text-sm text-gray-400">
                템플릿을 선택하고 파라미터를 입력해 SQL을 생성하세요.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">
                    카테고리
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {TEMPLATE_FILTER_OPTIONS.map(({ value, label, icon: Icon }) => (
                      <Button
                        key={value}
                        size="sm"
                        variant={templateFilter === value ? "default" : "outline"}
                        onClick={() => setTemplateFilter(value)}
                        className={cn(
                          "gap-2 transition-all",
                          templateFilter === value
                            ? "bg-emerald-500 hover:bg-emerald-600 text-white border-emerald-500/30 shadow-lg shadow-emerald-500/25"
                            : "bg-slate-900/50 hover:bg-slate-800/50 text-gray-300 border-emerald-500/20",
                        )}
                      >
                        <Icon className="h-3.5 w-3.5" />
                        {label}
                      </Button>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">
                    템플릿 선택
                  </label>
                  <select
                    value={selectedTemplate?.id ?? ""}
                    onChange={(event) => handleTemplateSelect(event.target.value)}
                    disabled={filteredTemplates.length === 0}
                    className="w-full rounded-lg border border-emerald-500/20 bg-slate-950/60 px-3 py-2 text-sm text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {filteredTemplates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.label}
                      </option>
                    ))}
                  </select>
                  <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground/80">
                    <span className="flex-1 pr-2">
                      {selectedTemplate?.description ??
                        (filteredTemplates.length === 0 ? "선택한 카테고리에 템플릿이 없습니다." : "선택된 템플릿 설명 없음")}
                    </span>
                    {selectedTemplate ? (
                      <Badge variant="outline" className="border-white/20 text-[10px] uppercase tracking-widest">
                        {TEMPLATE_CATEGORY_CONFIG[selectedTemplate.category ?? "other"].label}
                      </Badge>
                    ) : null}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground/70">
                    <span className={cn(toneToClass[templateStatus.tone])}>{templateStatus.message}</span>
                    <span>{filteredTemplates.length}개 표시</span>
                  </div>
                </div>
              </div>

              {selectedTemplate ? (
                <div className="space-y-3">
                  {(selectedTemplate.required_params ?? []).map((param) => (
                    <div key={param} className="space-y-1.5">
                      <label className="block text-xs font-medium text-gray-400">{param}</label>
                      <input
                        value={templateParams[param] ?? ""}
                        onChange={(event) => handleParamChange(param, event.target.value)}
                        className="w-full rounded-lg border border-emerald-500/20 bg-slate-950/60 px-3 py-2 text-sm text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                        placeholder={selectedTemplate.defaults?.[param] ?? "값 입력"}
                      />
                    </div>
                  ))}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <input
                      id="dry-run-toggle"
                      type="checkbox"
                      checked={dryRun}
                      onChange={(event) => setDryRun(event.target.checked)}
                      className="h-4 w-4 rounded border border-white/30 bg-slate-900/60"
                    />
                    <label htmlFor="dry-run-toggle">렌더링 후 즉시 Dry-run 실행</label>
                  </div>
                </div>
              ) : null}

              <div className="flex items-center justify-between gap-2">
                <span className={cn("text-xs", toneToClass[renderStatus.tone])}>{renderStatus.message}</span>
                <Button
                  onClick={renderTemplate}
                  disabled={!selectedTemplate}
                  className="gap-2 bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/25"
                >
                  <Wand2 className="h-4 w-4" /> 템플릿 렌더링
                </Button>
              </div>

              {renderResult ? (
                <div className="space-y-3 rounded-lg border border-white/10 bg-slate-950/60 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-foreground">렌더링된 SQL</span>
                    <Button variant="ghost" size="sm" className="text-xs" onClick={applySqlToPrompt}>
                      프롬프트에 적용
                    </Button>
                  </div>
                  {renderResult.warnings && renderResult.warnings.length > 0 ? (
                    <div className="space-y-2 rounded-md border border-amber-400/40 bg-amber-500/10 p-3 text-xs text-amber-100">
                      <div className="flex items-center gap-2 font-semibold uppercase tracking-widest">
                        <AlertTriangle className="h-4 w-4" /> 경고
                      </div>
                      <ul className="space-y-1">
                        {renderResult.warnings.map((warning, index) => (
                          <li key={index} className="leading-relaxed">
                            • {warning}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-md border border-white/5 bg-black/60 p-3 text-[11px] leading-relaxed text-muted-foreground">
                    {renderResult.sql}
                  </pre>
                  {renderResult.dry_run ? (
                    <div className="rounded-md border border-primary/30 bg-primary/5 p-3 text-xs text-primary">
                      Dry-run bytes: {renderResult.dry_run.total_bytes_processed ?? "-"}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-emerald-500/20 bg-gradient-to-br from-slate-900/90 to-slate-900/70 backdrop-blur-sm">
            <CardHeader className="space-y-3 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/20">
                  <Database className="h-4.5 w-4.5 text-emerald-400" />
                </div>
                <CardTitle className="text-lg font-bold text-white">
                  분석 요청 작성
                </CardTitle>
              </div>
              <CardDescription className="text-sm text-gray-400">
                BigQuery에 전달할 프롬프트를 입력하고 실시간 실행을 시작합니다.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <Textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="예) 최근 7일간 악성 앱 탐지 이벤트 추이를 알려줘"
                className="border-emerald-500/20 bg-slate-950/60 text-white focus:ring-emerald-500/50"
              />
              <div className="flex items-center justify-between gap-2">
                <span className={cn("text-sm", toneToClass[status.tone])}>{status.message}</span>
                <Button onClick={startRun} className="gap-2 bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/25">
                  <Play className="h-4 w-4" /> 실행
                </Button>
              </div>
              {runId ? (
                <div className="space-y-1 rounded-lg border border-white/10 bg-slate-900/40 p-3 text-xs text-muted-foreground">
                  <div>
                    <span className="font-medium text-foreground/80">run_id:</span> {runId}
                  </div>
                  <div>
                    <span className="font-medium text-foreground/80">session_id:</span> {sessionId}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>

        <Card className="border-emerald-500/20 bg-gradient-to-br from-slate-900/90 to-slate-900/70 backdrop-blur-sm">
          <CardHeader className="space-y-3 pb-4">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/20">
                <Activity className="h-4.5 w-4.5 text-emerald-400" />
              </div>
              <CardTitle className="text-lg font-bold text-white">라이브 이벤트 스트림</CardTitle>
            </div>
            <CardDescription className="text-sm text-gray-400">
              대화 흐름과 A2A/툴 호출을 요약으로 확인하고, Raw SSE 이벤트를 함께 살펴보세요.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="grid gap-6 xl:grid-cols-2">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span className="font-semibold text-foreground">대화 &amp; A2A 요약</span>
                  <Badge variant="outline" className="border-white/20 text-xs text-muted-foreground">
                    {conversationEntries.length} events
                  </Badge>
                </div>
                <ScrollArea className="h-[520px] rounded-xl border border-white/10 bg-slate-950/40">
                  <ScrollViewport className="h-full w-full space-y-4 p-6">
                    {conversationEntries.length === 0 ? (
                      <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-muted-foreground">
                        <p>표시할 대화 이벤트가 없습니다.</p>
                        <p className="text-xs">실행을 시작하면 에이전트와 하위 워크플로가 여기서 요약됩니다.</p>
                      </div>
                    ) : (
                      conversationEntries.map((entry) => {
                        const config = actorConfig[entry.actor]
                        const Icon = config.icon
                        return (
                          <div
                            key={entry.id}
                            className={cn(
                              "space-y-3 rounded-xl border bg-slate-900/70 p-4 shadow-sm transition",
                              config.cardClass,
                            )}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex items-center gap-3">
                                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10">
                                  <Icon className="h-4 w-4 text-foreground" />
                                </span>
                                <div>
                                  <p className="text-sm font-semibold text-foreground">{entry.title}</p>
                                  <p className="text-xs text-muted-foreground">{config.label}</p>
                                </div>
                              </div>
                              <span className="text-xs text-muted-foreground">
                                {new Date(entry.timestamp * 1000).toLocaleTimeString("ko-KR", {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                  second: "2-digit",
                                })}
                              </span>
                            </div>
                            <pre className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                              {entry.body}
                            </pre>
                            {entry.badges.length ? (
                              <div className="flex flex-wrap gap-2">
                                {entry.badges.map((badge) => (
                                  <Badge
                                    key={`${entry.id}-${badge}`}
                                    variant="outline"
                                    className={cn("bg-transparent text-[11px] uppercase tracking-wide", config.badgeClass)}
                                  >
                                    {badge}
                                  </Badge>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        )
                      })
                    )}
                  </ScrollViewport>
                </ScrollArea>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span className="font-semibold text-foreground">Raw SSE 이벤트</span>
                  <Badge variant="outline" className="border-white/20 text-xs text-muted-foreground">
                    {sortedEvents.length}
                  </Badge>
                </div>
                <ScrollArea className="h-[520px] rounded-xl border border-white/10 bg-slate-950/40">
                  <ScrollViewport className="h-full w-full space-y-4 p-6">
                    {sortedEvents.length === 0 ? (
                      <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-muted-foreground">
                        <p>수신된 이벤트가 없습니다.</p>
                        <p className="text-xs">실행을 시작하면 단계별 이벤트가 여기에 표시됩니다.</p>
                      </div>
                    ) : (
                      sortedEvents.map((event) => (
                        <div
                          key={`${event.sequence}-${event.name}`}
                          className="space-y-2 rounded-lg border border-white/10 bg-slate-900/80 p-4 shadow-sm"
                        >
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="border-primary/40 text-primary">
                                {event.name}
                              </Badge>
                              <span className="text-muted-foreground/70">#{event.sequence}</span>
                            </div>
                            <span>
                              {new Date(event.timestamp * 1000).toLocaleTimeString("ko-KR", {
                                hour: "2-digit",
                                minute: "2-digit",
                                second: "2-digit",
                              })}
                            </span>
                          </div>
                          <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-md border border-white/5 bg-black/60 p-3 text-[11px] leading-relaxed text-muted-foreground">
                            {JSON.stringify(event.payload, null, 2)}
                          </pre>
                        </div>
                      ))
                    )}
                  </ScrollViewport>
                </ScrollArea>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
