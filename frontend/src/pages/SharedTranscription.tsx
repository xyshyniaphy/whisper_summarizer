/**
 * SharedTranscription Page
 *
 * Public view for shared transcriptions (no authentication required).
 * Reuses TranscriptionDetail display components but hides AI Chat functionality.
 */

import { useEffect, useState, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AlertCircle, Loader2, Download, ChevronDown, File, FileText } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { cn } from '../utils/cn'

interface SharedTranscriptionData {
    id: string
    file_name: string
    text: string
    summary: string | null
    language: string | null
    duration_seconds: number | null
    created_at: string
}

// Reuse CollapsibleSection component from TranscriptionDetail
interface CollapsibleSectionProps {
    title: string
    children: React.ReactNode
    defaultOpen?: boolean
    headerContent?: React.ReactNode
}

function CollapsibleSection({ title, children, defaultOpen = true, headerContent }: CollapsibleSectionProps) {
    const [isOpen, setIsOpen] = useState(defaultOpen)

    return (
        <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800">
                <div className="flex items-center gap-2 flex-1">
                    <button
                        onClick={() => setIsOpen(!isOpen)}
                        className="flex items-center gap-2 font-medium hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                        aria-expanded={isOpen}
                    >
                        <ChevronDown
                            className={cn("w-5 h-5 transition-transform flex-shrink-0", isOpen && "rotate-180")}
                        />
                        {title}
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    {headerContent}
                </div>
            </div>
            {isOpen && (
                <div className="p-4 bg-white dark:bg-gray-900">
                    {children}
                </div>
            )}
        </div>
    )
}

export function SharedTranscription() {
    const { shareToken } = useParams()
    const navigate = useNavigate()
    const [data, setData] = useState<SharedTranscriptionData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const isLoadingRef = useRef(false)

    // PPTX generation state
    type PptxStatus = 'not-started' | 'generating' | 'ready' | 'error'
    const [pptxStatus, setPptxStatus] = useState<PptxStatus>('not-started')
    const pptxPollingRef = useRef(false)

    // Check PPTX status
    const checkPptxStatus = useCallback(async (transcriptionId: string) => {
        if (pptxPollingRef.current) return
        pptxPollingRef.current = true

        try {
            const result = await api.getPptxStatus(transcriptionId)
            setPptxStatus(result.exists ? 'ready' : 'not-started')
        } catch (e) {
            console.error('Failed to check PPTX status:', e)
        } finally {
            pptxPollingRef.current = false
        }
    }, [])

    const loadSharedTranscription = useCallback(async () => {
        if (isLoadingRef.current || !shareToken) return
        isLoadingRef.current = true

        try {
            setLoading(true)
            setError(null)
            const response = await api.getSharedTranscription(shareToken)
            setData(response)

            // Check PPTX status when loading transcription
            checkPptxStatus(response.id)
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
            isLoadingRef.current = false
        }
    }, [shareToken, checkPptxStatus])

    useEffect(() => {
        if (shareToken) {
            loadSharedTranscription()
        }
    }, [shareToken, loadSharedTranscription])

    // Reuse display text function from TranscriptionDetail (100 bytes preview)
    const getDisplayText = (text: string, maxBytes: number = 100): string => {
        const encoder = new TextEncoder()
        const encoded = encoder.encode(text)
        if (encoded.length <= maxBytes) {
            return text
        }
        // Find the character boundary near maxBytes
        let truncatedLength = maxBytes
        while (truncatedLength > 0 && (encoded[truncatedLength] & 0xC0) === 0x80) {
            truncatedLength--
        }
        const decoder = new TextDecoder('utf-8')
        return decoder.decode(encoded.slice(0, truncatedLength)) +
            `... (请下载完整版本查看)`
    }

    // Reuse download handlers from TranscriptionDetail
    const handleDownload = async (format: 'txt' | 'srt') => {
        if (!data) return
        try {
            const blob = await api.downloadFile(data.id, format)
            const link = document.createElement('a')
            link.href = URL.createObjectURL(blob)
            link.download = `${data.file_name.replace(/\.[^/.]+$/, '')}.${format}`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(link.href)
        } catch (error) {
            console.error('Download failed:', error)
            alert('下载失败')
        }
    }

    // Download DOCX
    const handleDownloadDocx = async () => {
        if (!data || !data.summary) return
        try {
            const blob = await api.downloadSummaryDocx(data.id)
            const link = document.createElement('a')
            link.href = URL.createObjectURL(blob)
            link.download = `${data.file_name.replace(/\.[^/.]+$/, '')}-摘要.docx`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(link.href)
        } catch (error) {
            console.error('DOCX download failed:', error)
            alert('DOCX下载失败')
        }
    }

    // Generate PPTX
    const handleGeneratePptx = async () => {
        if (!data) return
        try {
            const result = await api.generatePptx(data.id)
            if (result.status === 'ready') {
                setPptxStatus('ready')
            } else if (result.status === 'generating') {
                setPptxStatus('generating')
            }
        } catch (e) {
            console.error('Failed to generate PPTX:', e)
            setPptxStatus('error')
        }
    }

    // Download PPTX
    const handleDownloadPptx = async () => {
        if (!data) return
        try {
            const blob = await api.downloadFile(data.id, 'pptx')
            const link = document.createElement('a')
            link.href = URL.createObjectURL(blob)
            link.download = `${data.file_name.replace(/\.[^/.]+$/, '')}.pptx`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(link.href)
        } catch (error) {
            console.error('PPTX download failed:', error)
            alert('PPTX下载失败')
        }
    }

    // Poll for PPTX status when generating
    useEffect(() => {
        if (pptxStatus !== 'generating' || !data) {
            return
        }

        const interval = setInterval(() => {
            checkPptxStatus(data.id)
        }, 30000) // Poll every 30 seconds

        return () => clearInterval(interval)
    }, [pptxStatus, data, checkPptxStatus])

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
                <Button
                    variant="ghost"
                    className="mt-4"
                    onClick={() => navigate('/')}
                >
                    返回首页
                </Button>
            </div>
        )
    }

    const displayText = data.text ? getDisplayText(data.text, 100) : ''

    // Format duration as MM:SS
    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${String(secs).padStart(2, '0')}`
    }

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
                        <span>时长: {formatDuration(data.duration_seconds)}</span>
                    )}
                </div>
            )}

            <div className="space-y-6">
                {/* Transcription Text - Reusing CollapsibleSection */}
                <CollapsibleSection
                    title="转录结果"
                    defaultOpen={true}
                    headerContent={
                        data.text && (
                            <div className="flex gap-2 flex-wrap">
                                <button
                                    onClick={() => handleDownload('txt')}
                                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <Download className="w-4 h-4" />
                                    下载文本
                                </button>
                                <button
                                    onClick={() => handleDownload('srt')}
                                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <Download className="w-4 h-4" />
                                    下载字幕(SRT)
                                </button>
                            </div>
                        )
                    }
                >
                    {displayText ? (
                        <pre className="whitespace-pre-wrap font-sans text-sm">
                            {displayText}
                        </pre>
                    ) : (
                        <p className="text-gray-500 dark:text-gray-400 text-sm">
                            转录内容为空
                        </p>
                    )}
                </CollapsibleSection>

                {/* AI Summary - Reusing CollapsibleSection with Markdown */}
                {data.summary && (
                    <CollapsibleSection
                        title="AI摘要"
                        defaultOpen={true}
                        headerContent={
                            <div className="flex gap-2 flex-wrap">
                                {/* Download DOCX button */}
                                <button
                                    onClick={() => handleDownloadDocx()}
                                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors"
                                    title="下载Word文档"
                                >
                                    <File className="w-4 h-4" />
                                    下载DOCX
                                </button>
                                {/* PPTX button */}
                                {pptxStatus === 'ready' ? (
                                    <button
                                        onClick={() => handleDownloadPptx()}
                                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                                        title="下载PowerPoint演示文稿"
                                    >
                                        <FileText className="w-4 h-4" />
                                        下载PPT
                                    </button>
                                ) : pptxStatus === 'generating' ? (
                                    <button
                                        disabled
                                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-500 rounded-lg cursor-not-allowed"
                                    >
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        生成中...
                                    </button>
                                ) : pptxStatus === 'error' ? (
                                    <button
                                        onClick={() => handleGeneratePptx()}
                                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                                        title="重试生成PowerPoint演示文稿"
                                    >
                                        <FileText className="w-4 h-4" />
                                        重试生成PPT
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => handleGeneratePptx()}
                                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                                        title="生成PowerPoint演示文稿"
                                    >
                                        <FileText className="w-4 h-4" />
                                        生成PPT
                                    </button>
                                )}
                            </div>
                        }
                    >
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    h1: ({node, ...props}) => <h1 className="text-xl font-bold mb-4 pb-2 border-b dark:border-gray-700" {...props} />,
                                    h2: ({node, ...props}) => <h2 className="text-lg font-semibold mb-3 mt-6" {...props} />,
                                    h3: ({node, ...props}) => <h3 className="text-base font-semibold mb-2 mt-4" {...props} />,
                                    p: ({node, ...props}) => <p className="mb-3 leading-7" {...props} />,
                                    ul: ({node, ...props}) => <ul className="list-disc list-inside mb-3 space-y-1" {...props} />,
                                    ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-3 space-y-1" {...props} />,
                                    li: ({node, ...props}) => <li className="ml-4" {...props} />,
                                    code: ({node, className, ...props}) =>
                                        className
                                            ? <code className="block p-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-sm font-mono overflow-x-auto" {...props} />
                                            : <code className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-sm font-mono text-pink-600 dark:text-pink-400" {...props} />,
                                    pre: ({node, ...props}) => <pre className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto mb-3" {...props} />,
                                    blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic text-gray-600 dark:text-gray-400 my-3" {...props} />,
                                    a: ({node, ...props}) => <a className="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
                                    table: ({node, ...props}) => <div className="overflow-x-auto mb-3"><table className="min-w-full border border-gray-200 dark:border-gray-700" {...props} /></div>,
                                    thead: ({node, ...props}) => <thead className="bg-gray-50 dark:bg-gray-800" {...props} />,
                                    th: ({node, ...props}) => <th className="px-4 py-2 border border-gray-200 dark:border-gray-700 text-left font-semibold" {...props} />,
                                    td: ({node, ...props}) => <td className="px-4 py-2 border border-gray-200 dark:border-gray-700" {...props} />,
                                    hr: ({node, ...props}) => <hr className="my-4 border-gray-300 dark:border-gray-700" {...props} />,
                                    strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
                                    em: ({node, ...props}) => <em className="italic" {...props} />,
                                }}
                            >
                                {data.summary}
                            </ReactMarkdown>
                        </div>
                    </CollapsibleSection>
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
