import React, { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, AlertCircle, Loader2, Clock } from 'lucide-react'
import { api } from '../services/api'
import { Transcription } from '../types'
import { AudioUploader } from '../components/AudioUploader'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'

// Stage display mapping
const STAGE_LABELS: Record<string, string> = {
  uploading: '上传中',
  transcribing: '转录中',
  summarizing: '摘要生成中',
  completed: '已完成',
  failed: '失败'
}

interface DeleteConfirmState {
  isOpen: boolean
  id: string | null
  stage: string
}

export function TranscriptionList() {
    const [transcriptions, setTranscriptions] = useState<Transcription[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirmState>({
        isOpen: false,
        id: null,
        stage: ''
    })
    const navigate = useNavigate()

    const loadTranscriptions = useCallback(async () => {
        try {
            const data = await api.getTranscriptions()
            setTranscriptions(data)
        } catch (e) {
            console.error(e)
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        loadTranscriptions()
    }, [loadTranscriptions])

    const handleDeleteClick = (e: React.MouseEvent, id: string, stage: string) => {
        e.stopPropagation()
        e.preventDefault()
        setDeleteConfirm({ isOpen: true, id, stage })
    }

    const handleDeleteCancel = () => {
        setDeleteConfirm({ isOpen: false, id: null, stage: '' })
    }

    const handleDeleteConfirm = async () => {
        const { id } = deleteConfirm
        if (!id) return

        console.log('Proceeding with delete for id:', id)
        try {
            console.log('Calling API deleteTranscription...')
            await api.deleteTranscription(id)
            console.log('Delete successful, reloading list...')
            loadTranscriptions()
        } catch (e) {
            console.error('Delete failed:', e)
            alert('删除失败: ' + (e as Error).message)
        } finally {
            setDeleteConfirm({ isOpen: false, id: null, stage: '' })
        }
    }

    const getConfirmMessage = (stage: string): { title: string; message: string } => {
        if (stage === 'uploading' || stage === 'transcribing' || stage === 'summarizing') {
            return {
                title: '中止转录',
                message: '正在处理中，删除将中止转录进程。确定要删除吗？'
            }
        } else if (stage === 'failed') {
            return {
                title: '删除失败项',
                message: '失败的转录将被删除。确定要删除吗？'
            }
        } else if (stage === 'completed') {
            return {
                title: '删除已完成项',
                message: '已完成的转录将被删除，此操作无法撤销。确定要删除吗？'
            }
        }
        return {
            title: '确认删除',
            message: '确定要删除吗？'
        }
    }

    // Allow delete for all items (user can delete processing items to cancel them)
    const shouldAllowDelete = (_item: Transcription): boolean => {
        return true
    }

    const getBadgeVariant = (stage: string): 'success' | 'error' | 'info' | 'warning' => {
        if (stage === 'completed') return 'success'
        if (stage === 'failed') return 'error'
        if (stage === 'uploading') return 'warning'
        return 'info'
    }

    const formatUsedTime = (item: Transcription): string => {
        if (item.stage === 'completed' && item.completed_at) {
            const created = new Date(item.created_at).getTime()
            const completed = new Date(item.completed_at).getTime()
            const diff = (completed - created) / 1000 // seconds

            if (diff < 60) {
                return `${Math.floor(diff)}秒`
            } else if (diff < 3600) {
                const mins = Math.floor(diff / 60)
                const secs = Math.floor(diff % 60)
                return `${mins}分${secs}秒`
            } else {
                const hours = Math.floor(diff / 3600)
                const mins = Math.floor((diff % 3600) / 60)
                return `${hours}时${mins}分`
            }
        }
        return '-'
    }

    const formatAudioLength = (seconds?: number): string => {
        if (!seconds) return '-'
        if (seconds < 60) {
            return `${Math.floor(seconds)}秒`
        } else if (seconds < 3600) {
            const mins = Math.floor(seconds / 60)
            const secs = Math.floor(seconds % 60)
            return secs > 0 ? `${mins}分${secs}秒` : `${mins}分`
        } else {
            const hours = Math.floor(seconds / 3600)
            const mins = Math.floor((seconds % 3600) / 60)
            return mins > 0 ? `${hours}时${mins}分` : `${hours}时`
        }
    }

    const formatTimeRemaining = (seconds?: number): { text: string; className: string } => {
        if (seconds === undefined || seconds === null) {
            return { text: '-', className: 'text-gray-500 dark:text-gray-400' }
        }

        // Expired or will expire soon
        if (seconds <= 0) {
            return { text: '已过期', className: 'text-red-600 dark:text-red-400 font-medium' }
        }

        // Less than 1 day
        if (seconds < 86400) {
            if (seconds < 3600) {
                const mins = Math.ceil(seconds / 60)
                return { text: `${mins}分钟`, className: 'text-orange-600 dark:text-orange-400' }
            }
            const hours = Math.ceil(seconds / 3600)
            return { text: `${hours}小时`, className: 'text-orange-600 dark:text-orange-400' }
        }

        // 1-7 days
        if (seconds < 604800) {
            const days = Math.ceil(seconds / 86400)
            return { text: `${days}天`, className: 'text-yellow-600 dark:text-yellow-400' }
        }

        // More than 7 days
        const days = Math.ceil(seconds / 86400)
        return { text: `${days}天`, className: 'text-green-600 dark:text-green-400' }
    }

    const { title, message } = getConfirmMessage(deleteConfirm.stage)

    return (
        <div className="container mx-auto px-4 py-8">
            <h2 className="text-2xl font-bold mb-6">新建转录</h2>
            <AudioUploader />

            <h2 className="text-2xl font-bold mb-4 mt-8">转录历史</h2>
            <Card>
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-16">
                        <Loader2 className="w-10 h-10 text-blue-500 dark:text-blue-400 animate-spin" />
                        <p className="mt-4 text-gray-500 dark:text-gray-400">加载中...</p>
                    </div>
                ) : transcriptions.length > 0 ? (
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
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        音频时长
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        处理时间
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        <div className="flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            保留时间
                                        </div>
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
                                            {(item.retry_count ?? 0) > 0 && (
                                                <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                                                    重试 {item.retry_count} 次
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                                            {new Date(item.created_at).toLocaleString('zh-CN')}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                                            {formatAudioLength(item.duration_seconds)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                                            {formatUsedTime(item)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            <span className={formatTimeRemaining(item.time_remaining).className}>
                                                {formatTimeRemaining(item.time_remaining).text}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            {shouldAllowDelete(item) && (
                                                <button
                                                    onClick={(e) => handleDeleteClick(e, item.id, item.stage)}
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

            {/* Delete Confirmation Dialog */}
            <ConfirmDialog
                isOpen={deleteConfirm.isOpen}
                onClose={handleDeleteCancel}
                onConfirm={handleDeleteConfirm}
                title={title}
                message={message}
                confirmLabel="删除"
                cancelLabel="取消"
                variant="danger"
            />
        </div>
    )
}
