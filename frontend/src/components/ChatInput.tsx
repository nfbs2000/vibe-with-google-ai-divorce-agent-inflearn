import React, { useRef } from 'react'
import { Send, Paperclip, X, FileText, Image } from 'lucide-react'

import { Domain } from '../types'

interface ChatInputProps {
  domain: Domain
  inputValue: string
  files: File[]
  isBusy: boolean
  onChange: (value: string) => void
  onFilesChange: (files: File[]) => void
  onSubmit: () => void
  onKeyPress: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void
}

export const ChatInput: React.FC<ChatInputProps> = ({
  domain,
  inputValue,
  files,
  isBusy,
  onChange,
  onFilesChange,
  onSubmit,
  onKeyPress,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files)
      onFilesChange([...files, ...newFiles])
    }
    // Reset inputs so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeFile = (index: number) => {
    const newFiles = files.filter((_, i) => i !== index)
    onFilesChange(newFiles)
  }

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('image/')) return <Image className="w-4 h-4" />
    return <FileText className="w-4 h-4" />
  }

  return (
    <div className="bg-white border-t border-gray-200 px-6 py-4">
      {/* File Previews */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {files.map((file, idx) => (
            <div
              key={idx}
              className="flex items-center space-x-2 bg-gray-100 rounded-lg px-3 py-1.5 text-sm"
            >
              {getFileIcon(file)}
              <span className="truncate max-w-[200px] text-gray-700">
                {file.name}
              </span>
              <button
                onClick={() => removeFile(idx)}
                className="text-gray-400 hover:text-red-500 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <form
        onSubmit={(event) => {
          event.preventDefault()
          onSubmit()
        }}
        className="flex items-center gap-3"
      >
        {/* File Attach Button */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          multiple
          accept="image/*,video/*,audio/*,.pdf,.txt,.csv"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className={`flex-shrink-0 flex items-center justify-center w-[50px] h-[50px] rounded-2xl transition-colors transform -translate-y-[2px] ${domain === 'divorce_case'
              ? 'text-indigo-600 bg-indigo-50 hover:bg-indigo-100 hover:text-indigo-800'
              : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }`}
          disabled={isBusy}
          title={domain === 'divorce_case' ? "증거 파일 첨부 (사진, 녹음, 영상)" : "파일 첨부"}
        >
          <Paperclip className="w-6 h-6" />
        </button>

        <div className="flex-1 relative">
          <textarea
            value={inputValue}
            onChange={(e) => onChange(e.target.value)}
            onKeyPress={onKeyPress}
            placeholder="증거 사진, 녹음 파일을 업로드하거나 사건 내용을 입력하세요... (Shift+Enter로 줄바꿈)"
            className="w-full px-4 py-3 border border-gray-300 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent leading-normal scrollbar-hide text-base"
            rows={1}
            style={{ minHeight: '50px', maxHeight: '120px' }}
            disabled={isBusy}
          />
        </div>

        <button
          type="submit"
          disabled={isBusy || (!inputValue.trim() && files.length === 0)}
          className="flex-shrink-0 h-[50px] bg-blue-600 text-white px-6 rounded-2xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2 shadow-sm transform -translate-y-[2px]"
        >
          <Send className="w-5 h-5" />
          <span className="font-medium text-base">전송</span>
        </button>
      </form>
    </div>
  )
}
