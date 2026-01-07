/**
 * UnifiedProcessFlow - 통합 프로세스 흐름 시각화 컴포넌트
 *
 * 4-Layer 아키텍처의 실행 과정을 단계별로 시각화
 */
import React, { useState } from 'react'
import {
  ArrowRight,
  Target,
  BookOpen,
  Settings,
  Play,
  CheckCircle2,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronRight
} from 'lucide-react'

type StepStatus = 'pending' | 'in_progress' | 'completed' | 'error'

interface ProcessStep {
  layer: number
  name: string
  status: StepStatus
  data?: Record<string, any>
  details?: string[]
  timestamp?: string
}

interface UnifiedProcessFlowProps {
  steps: ProcessStep[]
  className?: string
}

interface LayerConfig {
  number: number
  title: string
  description: string
  icon: React.ReactNode
  color: string
  bgColor: string
}

const layerConfigs: LayerConfig[] = [
  {
    number: 1,
    title: 'Domain Router',
    description: '질문 키워드를 분석하여 Security, Conversion, Marketing, General 도메인 자동 분류',
    icon: <Target className="w-5 h-5" />,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50'
  },
  {
    number: 2,
    title: 'Domain Context',
    description: '분류된 도메인에 맞는 테이블, 메트릭, 비즈니스 규칙을 컨텍스트로 로드',
    icon: <BookOpen className="w-5 h-5" />,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50'
  },
  {
    number: 3,
    title: 'Execution Mode',
    description: 'SQL 직접 작성, Conversational AI 분석, 자동 선택 중 최적 실행 방식 결정',
    icon: <Settings className="w-5 h-5" />,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50'
  },
  {
    number: 4,
    title: 'Agent Execution',
    description: '선택된 에이전트(BigQuery/Conversational)가 Gemini 모델을 사용하여 쿼리 실행 및 분석',
    icon: <Play className="w-5 h-5" />,
    color: 'text-green-600',
    bgColor: 'bg-green-50'
  }
]

const getStatusIcon = (status: StepStatus) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-5 h-5 text-green-500" />
    case 'in_progress':
      return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
    case 'error':
      return <AlertCircle className="w-5 h-5 text-red-500" />
    default:
      return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
  }
}

const getStatusColor = (status: StepStatus) => {
  switch (status) {
    case 'completed':
      return 'border-green-200 bg-green-50'
    case 'in_progress':
      return 'border-blue-200 bg-blue-50 shadow-md'
    case 'error':
      return 'border-red-200 bg-red-50'
    default:
      return 'border-gray-200 bg-white'
  }
}

export const UnifiedProcessFlow: React.FC<UnifiedProcessFlowProps> = ({
  steps,
  className = ''
}) => {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())

  const toggleStep = (layer: number) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(layer)) {
      newExpanded.delete(layer)
    } else {
      newExpanded.add(layer)
    }
    setExpandedSteps(newExpanded)
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 shadow-sm ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">📊 분석 프로세스</h3>
        <p className="text-xs text-gray-500 mt-0.5">4단계 통합 아키텍처</p>
      </div>

      {/* Steps */}
      <div className="p-4 space-y-3">
        {layerConfigs.map((layer, idx) => {
          const step = steps.find(s => s.layer === layer.number)
          const status = step?.status || 'pending'
          const isExpanded = expandedSteps.has(layer.number)
          const hasDetails = step && (step.details || step.data)

          return (
            <div key={layer.number}>
              {/* Step Card */}
              <div
                className={`
                  border-2 rounded-lg transition-all
                  ${getStatusColor(status)}
                `}
              >
                {/* Step Header */}
                <button
                  onClick={() => hasDetails && toggleStep(layer.number)}
                  className={`
                    w-full px-4 py-3 flex items-center gap-3
                    ${hasDetails ? 'hover:bg-opacity-50 cursor-pointer' : 'cursor-default'}
                  `}
                  disabled={!hasDetails}
                >
                  {/* Status Icon */}
                  <div className="flex-shrink-0">
                    {getStatusIcon(status)}
                  </div>

                  {/* Layer Info */}
                  <div className="flex-1 text-left">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={`${layer.color}`}>{layer.icon}</span>
                      <span className="text-xs font-medium text-gray-500">
                        Layer {layer.number}
                      </span>
                    </div>
                    <h4 className="text-sm font-semibold text-gray-900">
                      {layer.title}
                    </h4>
                    <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                      {layer.description}
                    </p>
                  </div>

                  {/* Expand Icon */}
                  {hasDetails && (
                    <div className="flex-shrink-0 text-gray-400">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </div>
                  )}
                </button>

                {/* Step Details */}
                {isExpanded && step && (
                  <div className="px-4 pb-3 border-t border-gray-200 bg-white bg-opacity-50">
                    {/* Details List */}
                    {step.details && step.details.length > 0 && (
                      <div className="mt-3 space-y-1.5">
                        {step.details.map((detail, detailIdx) => (
                          <div key={detailIdx} className="flex items-start gap-2 text-xs">
                            <span className="text-gray-400 mt-0.5">•</span>
                            <span className="text-gray-700 flex-1">{detail}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Data Object */}
                    {step.data && Object.keys(step.data).length > 0 && (
                      <div className="mt-3 p-3 bg-gray-50 rounded border border-gray-200">
                        <div className="space-y-2">
                          {Object.entries(step.data).map(([key, value]) => (
                            <div key={key} className="flex items-start gap-2">
                              <span className="text-xs font-medium text-gray-600 min-w-[80px]">
                                {key}:
                              </span>
                              <span className="text-xs text-gray-800 flex-1 font-mono">
                                {typeof value === 'object'
                                  ? JSON.stringify(value, null, 2)
                                  : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Timestamp */}
                    {step.timestamp && (
                      <div className="mt-2 text-xs text-gray-400">
                        {step.timestamp}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Arrow Between Steps */}
              {idx < layerConfigs.length - 1 && (
                <div className="flex justify-center py-2">
                  <ArrowRight className="w-4 h-4 text-gray-300" />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 rounded-b-lg">
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-green-500" />
            <span className="text-gray-600">완료</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Loader2 className="w-4 h-4 text-blue-500" />
            <span className="text-gray-600">진행 중</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded-full border-2 border-gray-300" />
            <span className="text-gray-600">대기</span>
          </div>
          <div className="flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <span className="text-gray-600">오류</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default UnifiedProcessFlow
