import React, { useState, useRef, useEffect } from 'react'
import { Send, Bot } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { apiService } from '../services/api'
import { Message, QueryResponse } from '../types'
import { MessageBubble } from './MessageBubble'
import { ChartDisplay } from './ChartDisplay'
import { LoadingDots } from './LoadingDots'

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'assistant',
      content: '안녕하세요! 한국어로 데이터 분석 질문을 해주세요. 예: "지난 달 스미싱 건수는 몇 개인가요?"',
      timestamp: new Date()
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 메시지 스크롤
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 쿼리 처리 뮤테이션
  const queryMutation = useMutation({
    mutationFn: apiService.processQuery,
    onSuccess: (response: QueryResponse) => {
      const assistantMessage: Message = {
        id: Date.now().toString(),
        sender: 'assistant',
        content: response.response,
        timestamp: new Date(),
        queryResult: response
      }
      setMessages(prev => [...prev, assistantMessage])
    },
    onError: (error) => {
      const errorMessage: Message = {
        id: Date.now().toString(),
        sender: 'error',
        content: '죄송합니다. 쿼리 처리 중 오류가 발생했습니다. 다시 시도해주세요.',
        timestamp: new Date(),
        isError: true
      }
      setMessages(prev => [...prev, errorMessage])
      console.error('Query error:', error)
    }
  })

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!inputValue.trim() || queryMutation.isPending) return

    // 사용자 메시지 추가
    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMessage])

    // API 호출
    queryMutation.mutate({ query: inputValue.trim(), agent_type: 'sql' })
    setInputValue('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const exampleQueries = [
    '지난 달 스미싱 건수는 몇 개인가요?',
    '오늘 보안 이벤트 현황을 보여주세요',
    '가장 많이 발생한 악성앱 유형은?',
    '이번 주 사용자 활동 통계를 알려주세요'
  ]

  const handleExampleClick = (query: string) => {
    if (queryMutation.isPending) return
    setInputValue(query)
    inputRef.current?.focus()
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.map((message) => (
          <div key={message.id} className="animate-fade-in">
            <MessageBubble message={message} />
            {message.queryResult && message.queryResult.data?.length ? (
              <div className="mt-3 ml-12">
                <ChartDisplay queryResult={message.queryResult} />
              </div>
            ) : null}
          </div>
        ))}
        
        {/* 로딩 상태 */}
        {queryMutation.isPending && (
          <div className="flex items-start space-x-3 animate-slide-up">
            <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
              <Bot className="w-4 h-4 text-primary-600" />
            </div>
            <div className="bg-gray-100 rounded-lg px-4 py-3 max-w-xs">
              <LoadingDots />
              <span className="ml-2 text-sm text-gray-600">분석 중...</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 예시 쿼리 (메시지가 적을 때만 표시) */}
      {messages.length <= 2 && (
        <div className="px-4 py-2 border-t border-gray-100">
          <p className="text-sm text-gray-500 mb-2">예시 질문:</p>
          <div className="flex flex-wrap gap-2">
            {exampleQueries.map((query, index) => (
              <button
                key={index}
                onClick={() => handleExampleClick(query)}
                className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1 rounded-full transition-colors duration-200"
                disabled={queryMutation.isPending}
              >
                {query}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 입력 영역 */}
      <div className="border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="한국어로 데이터 분석 질문을 입력하세요..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              disabled={queryMutation.isPending}
            />
          </div>
          <button
            type="submit"
            disabled={!inputValue.trim() || queryMutation.isPending}
            className="px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 flex items-center justify-center"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
        
        <p className="text-xs text-gray-500 mt-2 text-center">
          Enter로 전송 • 한국어 자연어 쿼리를 지원합니다
        </p>
      </div>
    </div>
  )
}
