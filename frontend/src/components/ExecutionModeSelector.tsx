/**
 * ExecutionModeSelector - 실행 방식 선택 컴포넌트
 *
 * SQL 직접 작성 / AI 자동 분석 / 자동 선택 모드를 선택할 수 있는 UI
 */
import React from 'react'
import { Settings, Database, Sparkles, Zap } from 'lucide-react'

export type ExecutionMode = 'sql' | 'conversational' | 'auto'

interface ExecutionModeSelectorProps {
  selectedMode: ExecutionMode
  onModeChange: (mode: ExecutionMode) => void
  className?: string
}

interface ModeOption {
  value: ExecutionMode
  label: string
  icon: React.ReactNode
  description: string
  features: string[]
  color: string
  bgColor: string
  borderColor: string
}

const modeOptions: ModeOption[] = [
  {
    value: 'sql',
    label: 'SQL 직접 작성',
    icon: <Database className="w-5 h-5" />,
    description: '정밀한 제어',
    features: [
      'SQL 쿼리 직접 확인',
      '복잡한 조인 쿼리',
      '커스텀 분석'
    ],
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200'
  },
  {
    value: 'conversational',
    label: 'AI 자동 분석',
    icon: <Sparkles className="w-5 h-5" />,
    description: '빠르고 간편',
    features: [
      'SQL 지식 불필요',
      '빠른 분석 속도',
      '초보자 친화적'
    ],
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200'
  },
  {
    value: 'auto',
    label: '자동 선택',
    icon: <Zap className="w-5 h-5" />,
    description: '최적 모드 자동 선택',
    features: [
      '질문 특성 분석',
      '최적 방식 선택',
      '추천 모드'
    ],
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200'
  }
]

export const ExecutionModeSelector: React.FC<ExecutionModeSelectorProps> = ({
  selectedMode,
  onModeChange,
  className = ''
}) => {
  return (
    <div className={`bg-white rounded-lg border border-gray-200 shadow-sm ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
        <Settings className="w-5 h-5 text-gray-600" />
        <h3 className="text-sm font-semibold text-gray-900">실행 방식 설정</h3>
      </div>

      {/* Mode Options */}
      <div className="p-4 space-y-3">
        {modeOptions.map((option) => {
          const isSelected = selectedMode === option.value

          return (
            <button
              key={option.value}
              onClick={() => onModeChange(option.value)}
              className={`
                w-full text-left p-4 rounded-lg border-2 transition-all
                ${isSelected
                  ? `${option.bgColor} ${option.borderColor} shadow-md`
                  : 'bg-white border-gray-200 hover:border-gray-300'
                }
              `}
            >
              <div className="flex items-start gap-3">
                {/* Radio Button */}
                <div className="mt-0.5">
                  <div className={`
                    w-5 h-5 rounded-full border-2 flex items-center justify-center
                    ${isSelected ? option.borderColor : 'border-gray-300'}
                  `}>
                    {isSelected && (
                      <div className={`w-3 h-3 rounded-full ${option.color.replace('text-', 'bg-')}`} />
                    )}
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1">
                  {/* Title & Icon */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className={isSelected ? option.color : 'text-gray-400'}>
                      {option.icon}
                    </span>
                    <span className={`font-semibold ${isSelected ? 'text-gray-900' : 'text-gray-700'}`}>
                      {option.label}
                    </span>
                  </div>

                  {/* Description */}
                  <p className={`text-sm mb-2 ${isSelected ? 'text-gray-700' : 'text-gray-500'}`}>
                    {option.description}
                  </p>

                  {/* Features */}
                  <ul className="space-y-1">
                    {option.features.map((feature, idx) => (
                      <li key={idx} className={`text-xs flex items-center gap-1.5 ${
                        isSelected ? 'text-gray-600' : 'text-gray-400'
                      }`}>
                        <span className="text-green-500">✓</span>
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {/* Footer Info */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 rounded-b-lg">
        <p className="text-xs text-gray-500">
          💡 <strong>자동 선택</strong> 모드는 질문 특성을 분석하여 가장 적합한 방식을 자동으로 선택합니다.
        </p>
      </div>
    </div>
  )
}

export default ExecutionModeSelector
