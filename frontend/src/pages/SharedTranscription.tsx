/**
 * SharedTranscription Page
 *
 * Public view for shared transcriptions (no authentication required).
 * Users can only view the transcription and summary - no chat functionality.
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AlertCircle, Loader2 } from 'lucide-react'
import { api } from '../services/api'
import { Card, CardContent } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'

interface SharedTranscriptionData {
    id: string
    file_name: string
    text: string
    summary: string | null
    language: string | null
    duration_seconds: number | null
    created_at: string
}

// Display text with truncation
const getDisplayText = (text: string, maxLines: number = 200): string => {
    const lines = text.split('\n')
    if (lines.length <= maxLines) {
        return text
    }
    return lines.slice(0, maxLines).join('\n') +
        `\n\n... (剩余 ${lines.length - maxLines} 行) `
}

export function SharedTranscription() {
    const { shareToken } = useParams()
    const navigate = useNavigate()
    const [data, setData] = useState<SharedTranscriptionData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (shareToken) {
            loadSharedTranscription()
        }
    }, [shareToken])

    const loadSharedTranscription = async () => {
        try {
            setLoading(true)
            setError(null)
            const response = await api.getSharedTranscription(shareToken!)
            setData(response)
        } catch (err: any) {
            console.error('Failed to load shared transcription:', err)
            if (err.response?.status === 404) {
                setError('分享链接不存在')
            } else if (err.response?.status === 410) {
                setError('分享链接已过期')
            } else {
                setError('加载失败，请稍后再试')
            }
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8 flex justify-center items-center min-h-[50vh]">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-8 h-8 text-blue-500 dark:text-blue-400 animate-spin" />
                    <p className="text-gray-600 dark:text-gray-400">加载中...</p>
                </div>
            </div>
        )
    }

    if (error || !data) {
        return (
            <div className="container mx-auto px-4 py-8 max-w-2xl">
                <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
                    <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                        <p className="font-medium text-red-800 dark:text-red-200">加载失败</p>
                        <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error || '未找到转录内容'}</p>
                    </div>
                </div>
                <button
                    onClick={() => navigate('/')}
                    className="mt-4 px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                >
                    返回首页
                </button>
            </div>
        )
    }

    const displayText = data.text ? getDisplayText(data.text) : ''

    return (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                    <Badge variant="info">公开分享</Badge>
                </div>
                <h1 className="text-3xl font-bold mb-2">{data.file_name}</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                    创建于 {new Date(data.created_at).toLocaleString('zh-CN')}
                </p>
            </div>

            {/* Info Bar */}
            {(data.language || data.duration_seconds) && (
                <div className="mb-6 flex gap-4 text-sm text-gray-600 dark:text-gray-400">
                    {data.language && <span>语言: {data.language}</span>}
                    {data.duration_seconds && (
                        <span>时长: {Math.floor(data.duration_seconds / 60)}:{String(Math.floor(data.duration_seconds % 60)).padStart(2, '0')}</span>
                    )}
                </div>
            )}

            <div className="space-y-6">
                {/* Transcription Text */}
                <Card>
                    <CardContent className="pt-6">
                        <h3 className="text-lg font-semibold mb-4">转录结果</h3>
                        {displayText ? (
                            <pre className="whitespace-pre-wrap font-sans text-sm">
                                {displayText}
                            </pre>
                        ) : (
                            <p className="text-gray-500 dark:text-gray-400 text-sm">
                                转录内容为空
                            </p>
                        )}
                    </CardContent>
                </Card>

                {/* AI Summary */}
                {data.summary && (
                    <Card>
                        <CardContent className="pt-6">
                            <h3 className="text-lg font-semibold mb-4">AI摘要</h3>
                            <pre className="whitespace-pre-wrap font-sans text-sm">
                                {data.summary}
                            </pre>
                        </CardContent>
                    </Card>
                )}
            </div>

            {/* Footer */}
            <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
                <p className="text-center text-sm text-gray-500 dark:text-gray-400">
                    由 <a href="/" className="text-blue-600 dark:text-blue-400 hover:underline">Whisper Summarizer</a> 提供支持
                </p>
            </div>
        </div>
    )
}
