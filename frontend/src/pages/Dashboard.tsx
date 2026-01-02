import { useAuth } from '../hooks/useAuth'
import { Button } from '../components/ui/Button'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { api } from '../services/api'
import { Trash2, Loader2 } from 'lucide-react'
import { useState } from 'react'

interface DeleteAllConfirmState {
  isOpen: boolean
}

export default function Dashboard() {
    const [{ user }, { signOut }] = useAuth()
    const [isDeleting, setIsDeleting] = useState(false)
    const [deleteConfirm, setDeleteConfirm] = useState<DeleteAllConfirmState>({
        isOpen: false
    })

    const handleSignOut = async () => {
        const result = await signOut()
        if (result.error) {
            console.error('登出错误：', result.error.message)
        }
    }

    const handleDeleteAllClick = () => {
        setDeleteConfirm({ isOpen: true })
    }

    const handleDeleteAllCancel = () => {
        setDeleteConfirm({ isOpen: false })
    }

    const handleDeleteAllConfirm = async () => {
        setIsDeleting(true)
        setDeleteConfirm({ isOpen: false })
        try {
            const result = await api.deleteAllTranscriptions()
            alert(`${result.message}`)
        } catch (error) {
            console.error('Delete all error:', error)
            alert('删除失败: ' + (error as Error).message)
        } finally {
            setIsDeleting(false)
        }
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mt-10">仪表板</h1>

            <p className="mt-5">
                欢迎，{user?.email}
            </p>

            <p className="mt-5 text-gray-500 dark:text-gray-400 text-sm">
                音频文件上传功能正在开发中。
            </p>

            <div className="mt-8 flex gap-4">
                <Button
                    onClick={handleSignOut}
                    disabled={isDeleting}
                >
                    退出登录
                </Button>

                <Button
                    onClick={handleDeleteAllClick}
                    disabled={isDeleting}
                    variant="danger"
                    className="flex items-center gap-2"
                >
                    {isDeleting ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            删除中...
                        </>
                    ) : (
                        <>
                            <Trash2 className="w-4 h-4" />
                            删除所有音频
                        </>
                    )}
                </Button>
            </div>

            {/* Delete All Confirmation Dialog */}
            <ConfirmDialog
                isOpen={deleteConfirm.isOpen}
                onClose={handleDeleteAllCancel}
                onConfirm={handleDeleteAllConfirm}
                title="删除所有音频"
                message="确定要删除所有转录记录吗？此操作无法撤销。"
                confirmLabel="删除"
                cancelLabel="取消"
                variant="danger"
            />
        </div>
    )
}
