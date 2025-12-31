import React, { useState } from 'react'
import { Upload, X, FileAudio } from 'lucide-react'
import { api } from '../services/api'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent } from './ui/Card'

interface AudioUploaderProps {}

export function AudioUploader({}: AudioUploaderProps) {
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [isDragging, setIsDragging] = useState(false)
    const [isRejected, setIsRejected] = useState(false)

    const acceptedTypes = ['audio/mpeg', 'audio/wav', 'audio/aac', 'audio/flac', 'audio/ogg', 'audio/x-m4a', 'audio/mp4']
    const maxSize = 50 * 1024 * 1024 // 50MB

    const validateFile = (file: File): boolean => {
        if (!acceptedTypes.includes(file.type)) {
            setError('不支持的文件格式')
            setIsRejected(true)
            return false
        }
        if (file.size > maxSize) {
            setError('文件大小超过50MB')
            setIsRejected(true)
            return false
        }
        return true
    }

    const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        setIsDragging(false)
        setIsRejected(false)
        setError(null)

        const files = Array.from(e.dataTransfer.files)
        if (files.length > 0 && validateFile(files[0])) {
            await uploadFile(files[0])
        }
    }

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files
        if (files && files.length > 0) {
            setIsRejected(false)
            setError(null)
            if (validateFile(files[0])) {
                await uploadFile(files[0])
            }
        }
    }

    const uploadFile = async (file: File) => {
        setLoading(true)
        setError(null)
        try {
            const transcription = await api.uploadAudio(file)
            navigate(`/transcriptions/${transcription.id}`)
        } catch (err: any) {
            console.error(err)
            setError(err.response?.data?.detail || '上传失败')
        } finally {
            setLoading(false)
        }
    }

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const handleDragLeave = () => {
        setIsDragging(false)
    }

    return (
        <Card>
            <CardContent className="pt-6">
                <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    className={`
                        relative border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
                        ${isDragging
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : isRejected
                            ? 'border-red-300 dark:border-red-700'
                            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                        }
                        ${loading ? 'pointer-events-none opacity-50' : ''}
                    `}
                >
                    <input
                        type="file"
                        accept={acceptedTypes.join(',')}
                        onChange={handleFileSelect}
                        disabled={loading}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />

                    <div className="flex flex-col items-center justify-center gap-4 pointer-events-none min-h-[220px]">
                        {isRejected ? (
                            <X className="w-12 h-12 text-red-500" />
                        ) : isDragging ? (
                            <Upload className="w-12 h-12 text-blue-500" />
                        ) : (
                            <FileAudio className="w-12 h-12 text-gray-400 dark:text-gray-600" />
                        )}

                        <div>
                            <p className="text-lg font-medium">
                                将音频文件拖放到此处
                            </p>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                                或点击选择文件 (mp3, wav, m4a 等)
                            </p>
                        </div>

                        {loading && (
                            <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 rounded-lg">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
                            </div>
                        )}
                    </div>
                </div>

                {error && (
                    <p className="text-red-600 dark:text-red-400 mt-4 text-sm text-center">
                        {error}
                    </p>
                )}
            </CardContent>
        </Card>
    )
}
