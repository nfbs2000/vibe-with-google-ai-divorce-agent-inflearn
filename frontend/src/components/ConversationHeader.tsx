import React, { useState } from 'react'
import { Code, MessageSquare, ChevronDown, ChevronUp, Scale, Sparkles } from 'lucide-react'


type AgentType = 'sql' | 'conversational'

interface ConversationHeaderProps {
  agentType: AgentType
  onAgentTypeChange: (type: AgentType) => void
  executedModeLabel?: string | null
}

export const ConversationHeader: React.FC<ConversationHeaderProps> = ({
  agentType,
  onAgentTypeChange,
  executedModeLabel,
}) => {
  const [agentPanelCollapsed, setAgentPanelCollapsed] = useState(false)

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex flex-col gap-4">
        {/* Domain Label (Simplified) */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 px-3 py-2 bg-indigo-50 text-indigo-700 rounded-lg border border-indigo-100">
            <Scale className="w-4 h-4" />
            <span className="text-sm font-bold uppercase tracking-wide">Divorce Analysis Mode</span>
          </div>
          {executedModeLabel && (
            <div className="flex items-center space-x-2 px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-100 text-[11px] font-medium">
              <Sparkles className="w-3 h-3" />
              <span>{executedModeLabel}</span>
            </div>
          )}
        </div>

        {/* Agent Type Selection with Visualization */}
        <div className="flex flex-col gap-2">
          <button
            onClick={() => setAgentPanelCollapsed((prev) => !prev)}
            className="flex items-center justify-between text-sm font-semibold text-gray-700"
          >
            <span>에이전트 타입</span>
            {agentPanelCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>

          {!agentPanelCollapsed && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* SQL Agent Card */}
              <button
                onClick={() => onAgentTypeChange('sql')}
                className={`p-3 rounded-lg border transition-all text-left space-y-2 ${agentType === 'sql'
                  ? 'border-emerald-500 bg-emerald-50 shadow-sm'
                  : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
              >
                <div className="flex items-center space-x-2">
                  <div className={`p-1.5 rounded-md ${agentType === 'sql' ? 'bg-emerald-500' : 'bg-gray-200'}`}>
                    <Code className={`w-4 h-4 ${agentType === 'sql' ? 'text-white' : 'text-gray-600'}`} />
                  </div>
                  <div>
                    <h3 className={`text-sm font-bold ${agentType === 'sql' ? 'text-emerald-700' : 'text-gray-900'}`}>
                      SQL Agent
                    </h3>
                    <p className="text-[11px] text-gray-500">BigQuery 도구 + SQL</p>
                  </div>
                </div>
                <ul className="text-[11px] text-gray-600 space-y-0.5 pl-1 list-disc list-inside">
                  <li>템플릿 기반으로 빠르게 SQL 생성</li>
                  <li>Dry-run 검증 후 즉시 실행</li>
                  <li>도구 호출 로그가 상세히 남음</li>
                </ul>
              </button>

              {/* Conversational Agent Card */}
              <button
                onClick={() => onAgentTypeChange('conversational')}
                className={`p-3 rounded-lg border transition-all text-left space-y-2 ${agentType === 'conversational'
                  ? 'border-blue-500 bg-blue-50 shadow-sm'
                  : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
              >
                <div className="flex items-center space-x-2">
                  <div className={`p-1.5 rounded-md ${agentType === 'conversational' ? 'bg-blue-500' : 'bg-gray-200'}`}>
                    <MessageSquare className={`w-4 h-4 ${agentType === 'conversational' ? 'text-white' : 'text-gray-600'}`} />
                  </div>
                  <div>
                    <h3 className={`text-sm font-bold ${agentType === 'conversational' ? 'text-blue-700' : 'text-gray-900'}`}>
                      Conversational Agent
                    </h3>
                    <p className="text-[11px] text-gray-500">AI 대화형 분석</p>
                  </div>
                </div>
                <ul className="text-[11px] text-gray-600 space-y-0.5 pl-1 list-disc list-inside">
                  <li>질문 의도를 이해하고 자동 인사이트</li>
                  <li>카탈로그 검색 및 요약 제공</li>
                  <li>SQL 없이도 자연어로 설명</li>
                </ul>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
