/**
 * ChatDisplay Component
 *
 * Read-only display of AI chat messages.
 * Reusable across authenticated and shared views.
 */

import { useEffect, useRef } from 'react'
import { MessageCircle } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'

export interface ChatMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    created_at: string
}

interface ChatDisplayProps {
    messages: ChatMessage[]
    loading?: boolean
    error?: string | null
    emptyMessage?: string
    emptyDescription?: string
    className?: string
}

export function ChatDisplay({
    messages,
    loading = false,
    error = null,
    emptyMessage = '对此转录内容进行AI问答',
    emptyDescription = '提问关于此转录的任何问题，AI会根据转录内容进行回答。',
    className = '',
}: ChatDisplayProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Error state
    if (error) {
        return (
            <div className={`p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300 ${className}`}>
                {error}
            </div>
        )
    }

    // Empty state
    if (messages.length === 0) {
        return (
            <div className={`flex flex-col items-center justify-center py-12 text-center ${className}`}>
                <MessageCircle className="w-12 h-12 text-gray-400 dark:text-gray-600 mb-4" />
                <p className="text-gray-500 dark:text-gray-400 mb-2">
                    {emptyMessage}
                </p>
                <p className="text-sm text-gray-400 dark:text-gray-500 max-w-md">
                    {emptyDescription}
                </p>
            </div>
        )
    }

    // Messages display
    return (
        <div className={`space-y-4 max-h-[400px] overflow-y-auto ${className}`}>
            {messages.map((message) => (
                <div
                    key={message.id}
                    className={`flex ${
                        message.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                >
                    <div
                        className={`max-w-[80%] rounded-lg px-4 py-3 ${
                            message.role === 'user'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700'
                        }`}
                    >
                        {message.role === 'assistant' ? (
                            <div className="prose prose-sm dark:prose-invert max-w-none">
                                <MarkdownRenderer content={message.content} />
                            </div>
                        ) : (
                            <p className="text-sm whitespace-pre-wrap break-words">
                                {message.content}
                            </p>
                        )}
                    </div>
                </div>
            ))}
            <div ref={messagesEndRef} />
        </div>
    )
}
