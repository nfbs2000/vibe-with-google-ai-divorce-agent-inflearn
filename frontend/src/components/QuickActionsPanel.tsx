import React, { useState } from 'react'
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react'

type Domain = 'security' | 'conversion' | 'marketing' | 'general' | 'alyac_family' | 'audio_analytics' | 'divorce_case'
type Tone = 'blue' | 'violet' | 'emerald' | 'amber' | 'red' | 'orange'

interface QuickQuery {
  label: string
  value: string
  tone: Tone
}

interface QuickActionsPanelProps {
  domain: Domain
  executedModeLabel?: string | null
  quickQueries: QuickQuery[]
  isBusy: boolean
  onSelect: (value: string) => void
  hasMessages: boolean
}

export const QuickActionsPanel: React.FC<QuickActionsPanelProps> = ({
  domain,
  executedModeLabel,
  quickQueries,
  isBusy,
  onSelect,
  hasMessages,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const marginClass = hasMessages ? 'mb-4' : 'mb-8'

  return (
    <div
      className={`sticky top-0 z-10 bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg p-3 shadow-sm ${marginClass}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <h4 className="text-xs font-semibold text-gray-700">
            {domain === 'security' && 'Security 분석을 시작해보세요'}
            {domain === 'conversion' && 'Conversion 분석을 시작해보세요'}
            {domain === 'marketing' && 'Marketing 분석을 시작해보세요'}
            {domain === 'alyac_family' && '🛡️ ALYac Family 보안 분석을 시작해보세요'}
            {domain === 'audio_analytics' && '🎵 Audio Analytics 분석을 시작해보세요'}
            {domain === 'divorce_case' && '⚖️ 통합 이혼 솔루션 분석을 시작해보세요'}
            {domain === 'general' && 'BigQuery 데이터 분석을 시작해보세요'}
          </h4>
          {!isCollapsed && executedModeLabel && (
            <div className="mt-1 flex flex-col items-start space-y-1 text-[11px] sm:flex-row sm:items-center sm:space-y-0 sm:space-x-3">
              <span className="inline-flex items-center space-x-1 text-indigo-600 font-medium">
                <Sparkles className="w-3 h-3" />
                <span>실행 모드: {executedModeLabel}</span>
              </span>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => setIsCollapsed((prev) => !prev)}
          className="ml-3 inline-flex items-center rounded-md border border-gray-200 bg-white px-2 py-1 text-[11px] font-medium text-gray-600 hover:bg-gray-50"
        >
          {isCollapsed ? (
            <>
              <ChevronDown className="mr-1 h-3 w-3" />
              펼치기
            </>
          ) : (
            <>
              <ChevronUp className="mr-1 h-3 w-3" />
              접기
            </>
          )}
        </button>
      </div>
      {!isCollapsed && (
        <>
          <p className="text-xs text-gray-500 mb-3">
            {domain === 'security' && '예: "지난 달 스미싱 메시지가 몇 개나 있었나요?"'}
            {domain === 'conversion' && '예: "이번 주 구독 전환율은 어떻게 되나요?"'}
            {domain === 'marketing' && '예: "최근 캠페인 성과를 알려주세요"'}
            {domain === 'alyac_family' && '예: "위험한 권한을 가진 앱들을 분석해주세요"'}
            {domain === 'audio_analytics' && '예: "장르별 스토리 통계를 보여줘"'}
            {domain === 'divorce_case' && '예: "최근 위자료 산정 트렌드와 판례를 분석해줘"'}
            {domain === 'general' && '예: "최근 데이터 트렌드를 분석해주세요"'}
          </p>
          <div className="flex flex-wrap gap-2">
            {quickQueries.map((item, index) => (
              <button
                key={`${item.value}-${index}`}
                onClick={() => onSelect(item.value)}
                disabled={isBusy}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors border ${item.tone === 'blue'
                  ? 'border-blue-100 bg-blue-50 text-blue-700 hover:bg-blue-100'
                  : item.tone === 'violet'
                    ? 'border-violet-100 bg-violet-50 text-violet-700 hover:bg-violet-100'
                    : item.tone === 'emerald'
                      ? 'border-emerald-100 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                      : item.tone === 'amber'
                        ? 'border-amber-100 bg-amber-50 text-amber-700 hover:bg-amber-100'
                        : item.tone === 'red'
                          ? 'border-red-100 bg-red-50 text-red-700 hover:bg-red-100'
                          : 'border-orange-100 bg-orange-50 text-orange-700 hover:bg-orange-100'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
