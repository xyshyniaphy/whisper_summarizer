import React, { useCallback, useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, AlertCircle } from 'lucide-react'
import { api } from '../services/api'
import { Transcription } from '../types'
import { AudioUploader } from '../components/AudioUploader'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'

// Stage display mapping
const STAGE_LABELS: Record<string, string> = {
  uploading: '上传中',
  transcribing: '转录中',
  summarizing: '摘要生成中',
  completed: '已完成',
  failed: '失败'
}

export function TranscriptionList() {
    const [transcriptions, setTranscriptions] = useState<Transcription[]>([])
    const navigate = useNavigate()
    const isLoadingRef = useRef(false)

    const loadTranscriptions = useCallback(async () => {
        // Prevent duplicate calls (React 18 StrictMode)
        if (isLoadingRef.current) return
        isLoadingRef.current = true

        try {
            const data = await api.getTranscriptions()
            setTranscriptions(data)
        } catch (e) {
            console.error(e)
        } finally {
            isLoadingRef.current = false
        }
    }, [])

    useEffect(() => {
        loadTranscriptions()
    }, [loadTranscriptions])

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation()
        if (!window.confirm('确定要删除吗？')) return

        try {
            await api.deleteTranscription(id)
            loadTranscriptions()
        } catch (e) {
            console.error(e)
            alert('删除失败')
        }
    }

    // Check if item should show delete button (failed or > 24 hours old)
    const shouldAllowDelete = (item: Transcription): boolean => {
        if (item.stage === 'failed') return true
        if (item.stage !== 'completed') {
            const hoursSinceCreation = (Date.now() - new Date(item.created_at).getTime()) / (1000 * 60 * 60)
            if (hoursSinceCreation > 24) return true
        }
        return false
    }

    const getBadgeVariant = (stage: string): 'success' | 'error' | 'info' | 'warning' => {
        if (stage === 'completed') return 'success'
        if (stage === 'failed') return 'error'
        if (stage === 'uploading') return 'warning'
        return 'info'
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h2 className="text-2xl font-bold mb-6">新建转录</h2>
            <AudioUploader />

            <h2 className="text-2xl font-bold mb-4 mt-8">转录历史</h2>
            <Card>
                {transcriptions.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-900">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        文件名
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        状态
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        创建时间
                                    </th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        操作
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                {transcriptions.map((item) => (
                                    <tr
                                        key={item.id}
                                        className="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                                        onClick={() => navigate(`/transcriptions/${item.id}`)}
                                    >
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex flex-col">
                                                <span className="font-medium">{item.file_name}</span>
                                                {item.error_message && (
                                                    <span className="text-xs text-red-500 dark:text-red-400 flex items-center gap-1 mt-1">
                                                        <AlertCircle className="w-3 h-3" />
                                                        {item.error_message.length > 50
                                                            ? item.error_message.substring(0, 50) + '...'
                                                            : item.error_message}
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Badge variant={getBadgeVariant(item.stage)}>
                                                {STAGE_LABELS[item.stage] || item.stage}
                                            </Badge>
                                            {item.retry_count && item.retry_count > 0 && (
                                                <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                                                    重试 {item.retry_count} 次
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                                            {new Date(item.created_at).toLocaleString('zh-CN')}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            {shouldAllowDelete(item) && (
                                                <button
                                                    onClick={(e) => handleDelete(e, item.id)}
                                                    className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                                                    title="删除"
                                                >
                                                    <Trash2 className="w-5 h-5" />
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="text-center py-12 text-gray-500 dark:text-gray-400">
                        暂无数据
                    </p>
                )}
            </Card>
        </div>
    )
}
