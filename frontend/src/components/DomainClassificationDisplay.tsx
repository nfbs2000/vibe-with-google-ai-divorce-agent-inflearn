/**
 * DomainClassificationDisplay - 도메인 분류 결과 표시 컴포넌트
 *
 * 자동으로 분류된 도메인, 신뢰도 점수, 매칭된 키워드를 표시
 */
import React, { useState } from 'react'
import { Database, ChevronDown, ChevronUp, Target, Scale } from 'lucide-react'

export type Domain = 'general' | 'divorce_case'

interface DomainClassification {
  domain: Domain
  confidence: number
  matched_keywords: string[]
  suggested_tables: string[]
  reasoning: string
}

interface AlternativeDomain {
  domain: Domain
  confidence: number
}

interface DomainClassificationDisplayProps {
  classification: DomainClassification
  alternatives?: AlternativeDomain[]
  className?: string
}

interface DomainConfig {
  name: string
  icon: React.ReactNode
  color: string
  bgColor: string
  borderColor: string
  description: string
}

const domainConfigs: Record<Domain, DomainConfig> = {
  general: {
    name: '범용 데이터 분석',
    icon: <Database className="w-5 h-5" />,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    description: '일반적인 데이터 조회 및 탐색적 분석'
  },
  divorce_case: {
    name: '이혼 사례 분석',
    icon: <Scale className="w-5 h-5" />,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    borderColor: 'border-indigo-200',
    description: '이혼 소송 증거 분석 및 법적 판단 지원'
  }
}

const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return 'text-green-600'
  if (confidence >= 0.6) return 'text-amber-600'
  return 'text-orange-600'
}

const getConfidenceLabel = (confidence: number): string => {
  if (confidence >= 0.8) return '높은 신뢰도'
  if (confidence >= 0.6) return '중간 신뢰도'
  return '낮은 신뢰도'
}

export const DomainClassificationDisplay: React.FC<DomainClassificationDisplayProps> = ({
  classification,
  alternatives = [],
  className = ''
}) => {
  const [showDetails, setShowDetails] = useState(false)
  const config = domainConfigs[classification.domain]
  const confidencePercent = Math.round(classification.confidence * 100)

  return (
    <div className={`bg-white rounded-lg border border-gray-200 shadow-sm ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
        <Target className="w-5 h-5 text-gray-600" />
        <h3 className="text-sm font-semibold text-gray-900">분석 도메인</h3>
        <span className="ml-auto text-xs text-gray-500">(자동 선택됨)</span>
      </div>

      {/* Main Domain */}
      <div className={`p-4 ${config.bgColor} border-b-2 ${config.borderColor}`}>
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className={`${config.color}`}>
            {config.icon}
          </div>

          {/* Content */}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-semibold text-gray-900">{config.name}</h4>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${getConfidenceColor(classification.confidence)
                } bg-white border`}>
                {confidencePercent}%
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-2">{config.description}</p>

            {/* Confidence Bar */}
            <div className="mb-2">
              <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                <span>{getConfidenceLabel(classification.confidence)}</span>
                <span>{confidencePercent}%</span>
              </div>
              <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all ${classification.confidence >= 0.8 ? 'bg-green-500' :
                    classification.confidence >= 0.6 ? 'bg-amber-500' :
                      'bg-orange-500'
                    }`}
                  style={{ width: `${confidencePercent}%` }}
                />
              </div>
            </div>

            {/* Matched Keywords */}
            {classification.matched_keywords.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {classification.matched_keywords.slice(0, 5).map((keyword, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-1 bg-white border border-gray-300 rounded-md text-gray-700"
                  >
                    {keyword}
                  </span>
                ))}
                {classification.matched_keywords.length > 5 && (
                  <span className="text-xs text-gray-500 self-center">
                    +{classification.matched_keywords.length - 5}개
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Details Toggle */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="w-full px-4 py-2 flex items-center justify-between text-sm text-gray-600 hover:bg-gray-50 transition-colors"
      >
        <span>상세 정보</span>
        {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {/* Details Section */}
      {showDetails && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 space-y-3">
          {/* Reasoning */}
          <div>
            <h5 className="text-xs font-semibold text-gray-700 mb-1">분류 이유</h5>
            <p className="text-xs text-gray-600">{classification.reasoning}</p>
          </div>

          {/* Suggested Tables */}
          {classification.suggested_tables.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold text-gray-700 mb-1.5">관련 테이블</h5>
              <div className="flex flex-wrap gap-1.5">
                {classification.suggested_tables.map((table, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-1 bg-white border border-gray-200 rounded text-gray-700 font-mono"
                  >
                    {table.split('.').pop()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Alternative Domains */}
          {alternatives.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold text-gray-700 mb-1.5">대안 도메인</h5>
              <div className="space-y-1.5">
                {alternatives.map((alt, idx) => {
                  const altConfig = domainConfigs[alt.domain]
                  const altPercent = Math.round(alt.confidence * 100)
                  return (
                    <div key={idx} className="flex items-center gap-2">
                      <span className={`${altConfig.color}`}>{altConfig.icon}</span>
                      <span className="text-xs text-gray-700 flex-1">{altConfig.name}</span>
                      <span className="text-xs text-gray-500">{altPercent}%</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default DomainClassificationDisplay
