import { useCallback, useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, AlertCircle, FileText, Loader2 } from 'lucide-react'
import { api } from '../services/api'
import { Transcription, Summary } from '../types'
import { Button } from '../components/ui/Button'
import { Card, CardContent } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'

// Stage display mapping
const STAGE_LABELS: Record<string, string> = {
    uploading: '上传中',
    transcribing: '转录中',
    summarizing: '摘要生成中',
    completed: '已完成',
    failed: '失败'
}

// 表示用に最初の200行を取得
const getDisplayText = (text: string, maxLines: number = 200): string => {
    const lines = text.split('\n')
    if (lines.length <= maxLines) {
        return text
    }
    return lines.slice(0, maxLines).join('\n') +
        `\n\n... (剩余 ${lines.length - maxLines} 行。请下载完整版本)`
}

export function TranscriptionDetail() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [transcription, setTranscription] = useState<Transcription | null>(null)
    const [summary, setSummary] = useState<Summary | null>(null)
    const [loading, setLoading] = useState(true)
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

    const displayText = transcription.text
        ? getDisplayText(transcription.text, 200)
        : '转录完成后将自动生成。'

    const downloadUrlTxt = api.getDownloadUrl(transcription.id, 'txt')
    const downloadUrlSrt = api.getDownloadUrl(transcription.id, 'srt')

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
                <Badge variant={getBadgeVariant(transcription.stage)}>
                    {STAGE_LABELS[transcription.stage] || transcription.stage}
                </Badge>
            </div>

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
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-semibold">转录结果</h3>
                            {transcription.stage === 'completed' && (
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
                                    {/* PPTX button */}
                                    {pptxStatus === 'ready' ? (
                                        <button
                                            onClick={handleDownloadPptx}
                                            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
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
                                            onClick={handleGeneratePptx}
                                            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                                        >
                                            <FileText className="w-4 h-4" />
                                            重试生成PPT
                                        </button>
                                    ) : (
                                        <button
                                            onClick={handleGeneratePptx}
                                            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                                        >
                                            <FileText className="w-4 h-4" />
                                            生成PPT
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>
                        <pre className="whitespace-pre-wrap font-sans text-sm">
                            {displayText}
                        </pre>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="pt-6">
                        <h3 className="text-lg font-semibold mb-4">AI摘要</h3>
                        {summary ? (
                            <pre className="whitespace-pre-wrap font-sans text-sm">
                                {summary.summary_text}
                            </pre>
                        ) : (
                            <p className="text-gray-500 dark:text-gray-400 text-sm">
                                {transcription.stage === 'completed'
                                    ? '未找到摘要数据。'
                                    : transcription.stage === 'summarizing'
                                        ? '正在生成摘要...'
                                        : '转录完成后将自动生成摘要。'}
                            </p>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
