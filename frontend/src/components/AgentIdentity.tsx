import React from 'react'
import { BarChart3, Database, Layers, ShieldCheck, Sparkles } from 'lucide-react'
import { AgentMetadata, SqlGenerationDetails } from '../types'

const MODE_GRADIENTS: Record<string, string> = {
  schema_aware: 'from-emerald-500 via-teal-500 to-cyan-500',
  template: 'from-blue-500 via-indigo-500 to-purple-500',
  adk: 'from-amber-500 via-orange-500 to-rose-500',
  default: 'from-indigo-500 via-violet-500 to-sky-500',
}

const MODE_BADGE_CLASSES: Record<string, string> = {
  schema_aware: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
  template: 'bg-blue-100 text-blue-700 border border-blue-200',
  adk: 'bg-amber-100 text-amber-700 border border-amber-200',
  default: 'bg-gray-100 text-gray-700 border border-gray-200',
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

interface AgentIdentityProps {
  compact?: boolean
  className?: string
  agent?: AgentMetadata | null
  modelName?: string
  provider?: string
  executedModeLabel?: string
  sqlDetails?: SqlGenerationDetails | null
}

export const AgentIdentity: React.FC<AgentIdentityProps> = ({
  compact = false,
  className,
  agent,
  modelName,
  provider,
  executedModeLabel,
  sqlDetails,
}) => {
  const containerClasses = [
    'flex',
    'items-center',
    compact ? 'space-x-3' : 'space-x-4',
    className ?? '',
  ]
    .join(' ')
    .trim()

  const badgeSize = compact ? 'w-10 h-10' : 'w-12 h-12'
  const coreIconSize = compact ? 'w-5 h-5' : 'w-6 h-6'

  const modeKey = sqlDetails?.mode ?? undefined
  const gradientClass = MODE_GRADIENTS[modeKey ?? 'default'] ?? MODE_GRADIENTS.default
  const modeBadgeClass =
    MODE_BADGE_CLASSES[modeKey ?? 'default'] ?? MODE_BADGE_CLASSES.default
  const modeText = sqlDetails?.mode ? describeSqlMode(sqlDetails.mode) : (executedModeLabel ?? 'SQL 엔진')

  const title = agent?.display_name ?? 'ES Data Agent'
  const focus =
    agent?.focus ?? agent?.description ?? 'BigQuery 데이터 분석 전문가입니다.'

  const metaItems = [
    provider ? provider.toUpperCase() : null,
    modelName,
  ].filter(Boolean) as string[]

  const executionItems = [
    executedModeLabel ? `실행 모드: ${executedModeLabel}` : null,
  ].filter(Boolean) as string[]

  const strengthsRaw = Array.isArray(agent?.strengths)
    ? (agent?.strengths as string[])
    : []
  const strengths = strengthsRaw.filter((item) => typeof item === 'string' && item.trim())

  const displayStrengths = strengths.slice(0, compact ? 1 : 3)

  return (
    <div className={containerClasses}>
      <div className="relative">
        <div
          className={`${badgeSize} rounded-2xl bg-gradient-to-br ${gradientClass} shadow-lg flex items-center justify-center`}
        >
          <Database className={`${coreIconSize} text-white`} />
        </div>
        <Sparkles className="absolute -top-1 -right-1 w-4 h-4 text-amber-300 drop-shadow-sm" />
      </div>

      <div className="flex flex-col">
        <div className="flex items-center space-x-2">
          <span
            className={`${
              compact ? 'text-sm' : 'text-base'
            } font-semibold text-gray-900`}
          >
            {title}
          </span>
          {modeText && (
            <span
              className={`text-[11px] font-semibold px-2 py-0.5 rounded-full capitalize ${modeBadgeClass}`}
            >
              {modeText}
            </span>
          )}
        </div>
        <p
          className={`${compact ? 'text-xs' : 'text-sm'} text-gray-600 mt-1 leading-snug`}
        >
          {focus}
        </p>

        {metaItems.length > 0 && (
          <div
            className={`${
              compact ? 'mt-1 text-[11px]' : 'mt-2 text-xs'
            } text-gray-500 flex items-center space-x-2`}
          >
            {metaItems.map((item, index) => (
              <React.Fragment key={`${item}-${index}`}>
                {index > 0 && <span className="text-gray-400">•</span>}
                <span>{item}</span>
              </React.Fragment>
            ))}
          </div>
        )}

        {executionItems.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {executionItems.map((item, index) => (
              <span
                key={`${item}-${index}`}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] bg-slate-100 text-slate-600"
              >
                {item}
              </span>
            ))}
          </div>
        )}

        {!compact && displayStrengths.length > 0 && (
          <div className="mt-2 flex items-center space-x-2 text-gray-400" aria-hidden="true">
            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-100">
              <BarChart3 className="w-4 h-4" />
            </div>
            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-100">
              <Layers className="w-4 h-4" />
            </div>
            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-100">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
        )}

        {displayStrengths.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {displayStrengths.map((strength, index) => (
              <span
                key={`${strength}-${index}`}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] bg-gray-900 text-white/90"
              >
                {strength}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
