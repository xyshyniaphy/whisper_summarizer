import { useCallback, useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, AlertCircle, FileText, Loader2, File, Share2, Check, ChevronDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../services/api'
import { Transcription, Summary } from '../types'
import { Button } from '../components/ui/Button'
import { Card, CardContent } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Chat } from '../components/Chat'
import { cn } from '../utils/cn'

// Stage display mapping
const STAGE_LABELS: Record<string, string> = {
    uploading: '上传中',
    transcribing: '转录中',
    summarizing: '摘要生成中',
    completed: '已完成',
    failed: '失败'
}

// 表示用に最初の100バイトを取得
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

// Collapsible section component
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

export function TranscriptionDetail() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [transcription, setTranscription] = useState<Transcription | null>(null)
    const [summary, setSummary] = useState<Summary | null>(null)
    const [loading, setLoading] = useState(true)
    const isLoadingRef = useRef(false)

    // Share link state
    const [shareUrl, setShareUrl] = useState<string>('')
    const [shareCopied, setShareCopied] = useState(false)
    const [shareLoading, setShareLoading] = useState(false)

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

    const loadTranscription = useCallback(async (transcriptionId: string) => {
        // Prevent duplicate calls (React 18 StrictMode)
        if (isLoadingRef.current) return
        isLoadingRef.current = true

        try {
            const data = await api.getTranscription(transcriptionId)
            setTranscription(data)

            // 获取现有摘要（如果有）
            if (data.summaries && data.summaries.length > 0) {
                setSummary(data.summaries[0])
            }

            // Check PPTX status when loading transcription
            checkPptxStatus(transcriptionId)
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
            isLoadingRef.current = false
        }
    }, [checkPptxStatus])

    // Generate PPTX
    const handleGeneratePptx = async () => {
        if (!id) return

        try {
            const result = await api.generatePptx(id)
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
        if (!id) return

        try {
            const blob = await api.downloadFile(id, 'pptx')
            const link = document.createElement('a')
            link.href = URL.createObjectURL(blob)
            link.download = `${transcription?.file_name.replace(/\.[^/.]+$/, '')}.pptx`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(link.href)
        } catch (error) {
            console.error('PPTX download failed:', error)
            alert('PPTX下载失败')
        }
    }

    useEffect(() => {
        if (id) {
            loadTranscription(id)
        }
    }, [id, loadTranscription])

    // Poll for updates if not completed
    useEffect(() => {
        if (!transcription || transcription.stage === 'completed' || transcription.stage === 'failed') {
            return
        }

        const interval = setInterval(() => {
            if (id) {
                loadTranscription(id)
            }
        }, 3000) // Poll every 3 seconds

        return () => clearInterval(interval)
    }, [transcription, id, loadTranscription])

    // Poll for PPTX status when generating
    useEffect(() => {
        if (pptxStatus !== 'generating' || !id) {
            return
        }

        const interval = setInterval(() => {
            checkPptxStatus(id)
        }, 30000) // Poll every 30 seconds

        return () => clearInterval(interval)
    }, [pptxStatus, id, checkPptxStatus])

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8 flex justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
            </div>
        )
    }

    if (!transcription) {
        return (
            <div className="container mx-auto px-4 py-8">
                <p>未找到</p>
            </div>
        )
    }

    // Display AI-formatted transcription text (already formatted by backend)
    const displayText = transcription.text
        ? getDisplayText(transcription.text, 100)
        : '转录完成后将自动生成。'

    const handleDownload = async (format: 'txt' | 'srt') => {
        try {
            const blob = await api.downloadFile(transcription.id, format)

            // Create download link
            const link = document.createElement('a')
            link.href = URL.createObjectURL(blob)
            link.download = `${transcription.file_name.replace(/\.[^/.]+$/, '')}.${format}`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(link.href)
        } catch (error) {
            console.error('Download failed:', error)
            alert('下载失败')
        }
    }

    const handleDownloadDocx = async () => {
        if (!id || !summary) return

        try {
            const blob = await api.downloadSummaryDocx(id)
            const link = document.createElement('a')
            link.href = URL.createObjectURL(blob)
            link.download = `${transcription?.file_name.replace(/\.[^/.]+$/, '')}-摘要.docx`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(link.href)
        } catch (error) {
            console.error('DOCX download failed:', error)
            alert('DOCX下载失败')
        }
    }

    const handleShare = async () => {
        if (!id) return

        try {
            setShareLoading(true)
            const result = await api.createShareLink(id)
            // Construct full URL for sharing
            const fullUrl = `${window.location.origin}${result.share_url}`
            setShareUrl(fullUrl)
        } catch (error) {
            console.error('Failed to create share link:', error)
            alert('生成分享链接失败')
        } finally {
            setShareLoading(false)
        }
    }

    const handleCopyShareLink = async () => {
        try {
            await navigator.clipboard.writeText(shareUrl)
            setShareCopied(true)
            setTimeout(() => setShareCopied(false), 2000)
        } catch (error) {
            console.error('Failed to copy:', error)
        }
    }

    const getBadgeVariant = (stage: string): 'success' | 'error' | 'info' | 'warning' => {
        if (stage === 'completed') return 'success'
        if (stage === 'failed') return 'error'
        if (stage === 'uploading') return 'warning'
        return 'info'
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
            <Button
                variant="ghost"
                className="mb-4"
                onClick={() => navigate('/transcriptions')}
            >
                ← 返回列表
            </Button>

            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">{transcription.file_name}</h2>
                <div className="flex gap-2 items-center">
                    <Badge variant={getBadgeVariant(transcription.stage)}>
                        {STAGE_LABELS[transcription.stage] || transcription.stage}
                    </Badge>
                    <button
                        onClick={handleShare}
                        disabled={shareLoading}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-lg hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="生成分享链接"
                    >
                        <Share2 className="w-4 h-4" />
                        {shareLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : '分享'}
                    </button>
                </div>
            </div>

            {/* Share Link Modal */}
            {shareUrl && (
                <div className="mb-6 p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
                    <p className="text-sm font-medium text-purple-900 dark:text-purple-100 mb-2">分享链接已生成</p>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            readOnly
                            value={shareUrl}
                            className="flex-1 px-3 py-2 bg-white dark:bg-gray-800 border border-purple-300 dark:border-purple-700 rounded-lg text-sm"
                        />
                        <button
                            onClick={handleCopyShareLink}
                            className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors flex items-center gap-2"
                        >
                            {shareCopied ? <Check className="w-4 h-4" /> : '复制'}
                        </button>
                    </div>
                    <p className="text-xs text-purple-700 dark:text-purple-300 mt-2">
                        任何人都可以通过此链接查看转录内容，无需登录。
                    </p>
                </div>
            )}

            {transcription.error_message && (
                <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                        <p className="font-medium text-red-800 dark:text-red-200">处理失败</p>
                        <p className="text-sm text-red-600 dark:text-red-300 mt-1">{transcription.error_message}</p>
                    </div>
                </div>
            )}

            <div className="space-y-6">
                {/* Transcription Result - Collapsible */}
                <CollapsibleSection
                    title="转录结果"
                    defaultOpen={true}
                    headerContent={
                        transcription.stage === 'completed' && (
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
                    <pre className="whitespace-pre-wrap font-sans text-sm">
                        {displayText}
                    </pre>
                </CollapsibleSection>

                {/* AI Summary - Collapsible with Markdown */}
                <CollapsibleSection
                    title="AI摘要"
                    defaultOpen={true}
                    headerContent={
                        summary && transcription.stage === 'completed' && (
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
                        )
                    }
                >
                    {summary ? (
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    // GitHub-flavored markdown styling
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
                                {summary.summary_text}
                            </ReactMarkdown>
                        </div>
                    ) : (
                        <p className="text-gray-500 dark:text-gray-400 text-sm">
                            {transcription.stage === 'completed'
                                ? '未找到摘要数据。'
                                : transcription.stage === 'summarizing'
                                    ? '正在生成摘要...'
                                    : '转录完成后将自动生成摘要。'}
                        </p>
                    )}
                </CollapsibleSection>

                {/* AI Chat Section */}
                {transcription.stage === 'completed' && id && (
                    <Card>
                        <CardContent className="pt-6">
                            <h3 className="text-lg font-semibold mb-4">AI 问答</h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                                基于转录内容向AI提问，获取更详细的信息。
                            </p>
                            <Chat transcriptionId={id} />
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    )
}
