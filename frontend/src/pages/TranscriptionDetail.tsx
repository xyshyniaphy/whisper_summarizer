import { useCallback, useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, AlertCircle } from 'lucide-react'
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
        `\n\n... (残り ${lines.length - maxLines} 行。完全版はダウンロードしてください)`
}

export function TranscriptionDetail() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [transcription, setTranscription] = useState<Transcription | null>(null)
    const [summary, setSummary] = useState<Summary | null>(null)
    const [loading, setLoading] = useState(true)
    const isLoadingRef = useRef(false)

    const loadTranscription = useCallback(async (transcriptionId: string) => {
        // Prevent duplicate calls (React 18 StrictMode)
        if (isLoadingRef.current) return
        isLoadingRef.current = true

        try {
            const data = await api.getTranscription(transcriptionId)
            setTranscription(data)

            // 既存の要約があれば取得
            if (data.summaries && data.summaries.length > 0) {
                setSummary(data.summaries[0])
            }
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
            isLoadingRef.current = false
        }
    }, [])

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
                <p>見つかりませんでした</p>
            </div>
        )
    }

    const displayText = transcription.original_text
        ? getDisplayText(transcription.original_text, 200)
        : '文字起こし中、または結果がありません...'

    const downloadUrlTxt = api.getDownloadUrl(transcription.id, 'txt')
    const downloadUrlSrt = api.getDownloadUrl(transcription.id, 'srt')

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
                ← 一覧に戻る
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
                            <h3 className="text-lg font-semibold">文字起こし結果</h3>
                            {transcription.stage === 'completed' && (
                                <div className="flex gap-2">
                                    <a
                                        href={downloadUrlTxt}
                                        download
                                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                    >
                                        <Download className="w-4 h-4" />
                                        テキストをダウンロード
                                    </a>
                                    <a
                                        href={downloadUrlSrt}
                                        download
                                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                    >
                                        <Download className="w-4 h-4" />
                                        字幕（SRT）をダウンロード
                                    </a>
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
                        <h3 className="text-lg font-semibold mb-4">AI要約</h3>
                        {summary ? (
                            <pre className="whitespace-pre-wrap font-sans text-sm">
                                {summary.summary_text}
                            </pre>
                        ) : (
                            <p className="text-gray-500 dark:text-gray-400 text-sm">
                                {transcription.stage === 'completed'
                                    ? '要約データが見つかりません。'
                                    : transcription.stage === 'summarizing'
                                        ? '要約を生成中...'
                                        : '文字起こしが完了すると自動的に要約を生成します。'}
                            </p>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
