import React from 'react'

export interface LogEntry {
  id: string
  source: 'frontend' | 'backend'
  message: string
  timestamp: Date
}

interface LogPanelProps {
  logs: LogEntry[]
  logsEndRef: React.RefObject<HTMLDivElement>
}

export function LogPanel({ logs, logsEndRef }: LogPanelProps) {
  if (logs.length === 0) {
    return null
  }

  return (
    <div className="mt-4 border-t border-gray-200 pt-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-700">
          🔍 실시간 SSE 스트림 로그 ({logs.length}개)
        </h3>
        <span className="text-xs text-gray-500">투명한 AI 처리 과정</span>
      </div>

      <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto font-mono text-xs">
        {logs.map((log) => (
          <div
            key={log.id}
            className={`mb-2 pb-2 border-b border-gray-700 last:border-b-0 ${
              log.source === 'backend' ? 'text-green-400' : 'text-blue-400'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-gray-500">
                {log.timestamp.toLocaleTimeString('ko-KR', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                  fractionalSecondDigits: 3
                })}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-semibold ${
                  log.source === 'backend'
                    ? 'bg-green-900 text-green-300'
                    : 'bg-blue-900 text-blue-300'
                }`}
              >
                {log.source}
              </span>
            </div>
            <pre className="whitespace-pre-wrap break-words">{log.message}</pre>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}
