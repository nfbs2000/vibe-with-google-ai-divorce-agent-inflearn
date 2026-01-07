import React from 'react'
import { Sparkles, Bot } from 'lucide-react'

import { Message } from '../types'
import { MessageBubble } from './MessageBubble'
import { ChartDisplay } from './ChartDisplay'
import { LoadingDots } from './LoadingDots'

interface MessageSectionProps {
  messages: Message[]
  isBusy: boolean
  onFeedback: (messageId: string, type: 'like' | 'dislike') => void
  messagesEndRef: React.RefObject<HTMLDivElement>
}

export const MessageSection: React.FC<MessageSectionProps> = ({
  messages,
  isBusy,
  onFeedback,
  messagesEndRef,
}) => {
  const hasMessages = messages.length > 0

  if (!hasMessages) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 'calc(100vh - 400px)' }}>
        <div className="text-center max-w-xl">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">위의 예시 질문을 클릭하거나</h3>
          <p className="text-gray-600">아래 입력창에 직접 질문을 입력해보세요</p>
        </div>
      </div>
    )
  }

  return (
    <>
      {messages.map((message) => (
        <div key={message.id}>
          <MessageBubble message={message} onFeedback={onFeedback} />
          {message.queryResult && message.queryResult.data?.length ? (
            <div className="mt-4">
              <ChartDisplay queryResult={message.queryResult} />
            </div>
          ) : null}
        </div>
      ))}

      {isBusy && (
        <div className="flex items-center space-x-2 text-gray-500">
          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <div className="w-4 h-4 bg-blue-600 rounded-full animate-ping" />
          </div>
          <div className="bg-white rounded-lg px-4 py-2 shadow-sm border flex items-center space-x-2">
            <Bot className="w-4 h-4 text-blue-600" />
            <LoadingDots />
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </>
  )
}
