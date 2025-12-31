import React, { useCallback, useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import { api } from '../services/api'
import { Transcription } from '../types'
import { AudioUploader } from '../components/AudioUploader'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'

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
        if (!window.confirm('本当に削除しますか？')) return

        try {
            await api.deleteTranscription(id)
            loadTranscriptions()
        } catch (e) {
            console.error(e)
            alert('削除に失敗しました')
        }
    }

    const getBadgeVariant = (status: string): 'success' | 'error' | 'info' => {
        if (status === 'completed') return 'success'
        if (status === 'failed') return 'error'
        return 'info'
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h2 className="text-2xl font-bold mb-6">新しい文字起こし</h2>
            <AudioUploader />

            <h2 className="text-2xl font-bold mb-4 mt-8">文字起こし履歴</h2>
            <Card>
                {transcriptions.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-900">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        ファイル名
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        ステータス
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        作成日時
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
                                            {item.file_name}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Badge variant={getBadgeVariant(item.status)}>
                                                {item.status}
                                            </Badge>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                                            {new Date(item.created_at).toLocaleString('ja-JP')}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <button
                                                onClick={(e) => handleDelete(e, item.id)}
                                                className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                                                title="削除"
                                            >
                                                <Trash2 className="w-5 h-5" />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="text-center py-12 text-gray-500 dark:text-gray-400">
                        データがありません
                    </p>
                )}
            </Card>
        </div>
    )
}
