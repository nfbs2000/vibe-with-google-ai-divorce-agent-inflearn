import React from 'react'
import { Settings, HelpCircle } from 'lucide-react'
import { AgentIdentity } from './AgentIdentity'

export const Header: React.FC = () => {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* 로고 및 제목 */}
        <AgentIdentity />

        {/* 우측 액션 버튼들 */}
        <div className="flex items-center space-x-2">
          <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors duration-200">
            <HelpCircle className="w-5 h-5" />
          </button>
          <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors duration-200">
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  )
}
