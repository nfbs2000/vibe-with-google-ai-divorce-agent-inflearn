import React from 'react'
import { Database, MessageSquare, Clock } from 'lucide-react'
import { DataSource, SystemStatus } from '../types'

interface SidebarProps {
  dataSources?: DataSource[]
  systemStatus?: SystemStatus | null
  onExampleQuery?: (query: string) => void
  exampleQueries?: string[]
}

const defaultDataSources = [
  {
    icon: MessageSquare,
    name: '이혼 판례 DB',
    description: '61개 핵심 판례 데이터',
    count: '61',
    color: 'text-indigo-600 bg-indigo-100'
  }
]

const defaultQueries = [
  '최근 위자료 산정 기준은?',
  '재산분할 기여도 산정 방식',
  '양육권 지정 시 고려사항',
  '부정행위 증거 효력 분석'
]

export const Sidebar: React.FC<SidebarProps> = ({
  dataSources,
  systemStatus,
  onExampleQuery,
  exampleQueries
}) => {
  const categories = dataSources && dataSources.length > 0
    ? dataSources.map((source) => ({
      icon: MessageSquare,
      name: source.display_name || source.name,
      description: source.description,
      count: source.total_rows?.toLocaleString() ?? '-',
      color: source.status === 'active' ? 'text-blue-600 bg-blue-100' : 'text-gray-500 bg-gray-100'
    }))
    : defaultDataSources

  const queries = exampleQueries && exampleQueries.length > 0 ? exampleQueries : defaultQueries

  return (
    <aside className="w-80 bg-white border-r border-gray-200 flex flex-col min-h-0">
      {/* 사이드바 헤더 */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center space-x-2 mb-4">
          <Database className="w-5 h-5 text-primary-600" />
          <h2 className="font-semibold text-gray-900">데이터 소스</h2>
        </div>
        <p className="text-sm text-gray-500">
          BigQuery에서 실시간으로 데이터를 분석합니다
        </p>
      </div>

      {/* 스크롤 가능한 본문 */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6 custom-scrollbar">
        <section>
          <h3 className="text-sm font-medium text-gray-700 mb-3">사용 가능한 데이터</h3>
          <div className="space-y-3">
            {categories.map((category, index) => {
              const IconComponent = category.icon
              return (
                <div
                  key={index}
                  className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors duration-200 cursor-pointer card-hover"
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${category.color}`}>
                    <IconComponent className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {category.name}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {category.description}
                    </p>
                  </div>
                  <div className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-1 rounded-full">
                    {category.count}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        <section className="border-t border-gray-100 pt-4">
          <div className="flex items-center space-x-2 mb-3">
            <Clock className="w-4 h-4 text-gray-500" />
            <h3 className="text-sm font-medium text-gray-700">최근 질문</h3>
          </div>
          <div className="space-y-2">
            {queries.map((query, index) => (
              <button
                key={index}
                onClick={() => onExampleQuery && onExampleQuery(query)}
                className="w-full text-left text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 p-2 rounded-md transition-colors duration-200 truncate"
              >
                {query}
              </button>
            ))}
          </div>
        </section>
      </div>

      {/* 상태 정보 */}
      <div className="mt-auto p-6 border-t border-gray-100">
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full animate-pulse ${systemStatus?.bigquery_connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className={`text-sm font-medium ${systemStatus?.bigquery_connected ? 'text-green-800' : 'text-red-800'}`}>
              {systemStatus?.bigquery_connected ? 'BigQuery 연결됨' : 'BigQuery 연결 필요'}
            </span>
          </div>
          <p className="text-xs text-green-600 mt-1">
            {systemStatus?.last_health_check
              ? `마지막 헬스체크: ${new Date(systemStatus.last_health_check).toLocaleString()}`
              : '실시간 데이터 분석 상태 확인'}
          </p>
          <div className="mt-3 text-xs text-green-700 space-y-1">
            <div>
              모델: {systemStatus?.model_name ? `${systemStatus.model_name}` : '확인 중'}
              {systemStatus?.model_provider ? ` (${systemStatus.model_provider})` : ''}
            </div>
            <div className="text-green-600">
              {systemStatus?.sql_description ?? 'LLM + 템플릿으로 SQL을 동적으로 생성합니다.'}
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
