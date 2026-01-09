/**
 * User Management Tab for Admin Dashboard
 * Allows admins to activate users, toggle admin status, and delete users
 */

import { useState, useEffect } from 'react'
import { adminApi } from '../../services/api'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { Loader2, Shield, ShieldCheck, UserCheck, UserX, Trash2 } from 'lucide-react'

interface User {
  id: string
  email: string
  is_active: boolean
  is_admin: boolean
  activated_at: string | null
  created_at: string
}

interface DeleteConfirmState {
  isOpen: boolean
  userId: string | null
  userEmail: string | null
}

export function UserManagementTab() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirmState>({
    isOpen: false,
    userId: null,
    userEmail: null,
  })

  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminApi.listUsers()
      setUsers(data)
    } catch (err) {
      console.error('Error fetching users:', err)
      setError('加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleActivateUser = async (userId: string) => {
    setActionLoading(userId)
    try {
      await adminApi.activateUser(userId)
      await fetchUsers()
    } catch (err) {
      console.error('Error activating user:', err)
      alert('激活用户失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleToggleAdmin = async (userId: string, currentStatus: boolean) => {
    setActionLoading(userId)
    try {
      await adminApi.toggleUserAdmin(userId, !currentStatus)
      await fetchUsers()
    } catch (err) {
      console.error('Error toggling admin:', err)
      alert('更改管理员权限失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDeleteClick = (userId: string, userEmail: string) => {
    setDeleteConfirm({ isOpen: true, userId, userEmail })
  }

  const handleDeleteCancel = () => {
    setDeleteConfirm({ isOpen: false, userId: null, userEmail: null })
  }

  const handleDeleteConfirm = async () => {
    if (!deleteConfirm.userId) return

    setActionLoading(deleteConfirm.userId)
    setDeleteConfirm({ isOpen: false, userId: null, userEmail: null })

    try {
      await adminApi.deleteUser(deleteConfirm.userId)
      await fetchUsers()
    } catch (err) {
      console.error('Error deleting user:', err)
      alert('删除用户失败: ' + (err as Error).message)
    } finally {
      setActionLoading(null)
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-10 h-10 text-primary-600 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <Button onClick={fetchUsers} className="mt-4">
          重试
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">总用户数</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">{users.length}</p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">已激活用户</p>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
            {users.filter(u => u.is_active).length}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">管理员</p>
          <p className="text-2xl font-bold text-primary-600 dark:text-primary-400 mt-1">
            {users.filter(u => u.is_admin).length}
          </p>
        </div>
      </div>

      {/* Users table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b dark:border-gray-700">
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">邮箱</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">状态</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">权限</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">创建时间</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">激活时间</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">操作</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="py-3 px-4 text-gray-900 dark:text-gray-100">{user.email}</td>
                <td className="py-3 px-4">
                  {user.is_active ? (
                    <Badge variant="success">已激活</Badge>
                  ) : (
                    <Badge variant="warning">待激活</Badge>
                  )}
                </td>
                <td className="py-3 px-4">
                  {user.is_admin ? (
                    <Badge variant="info" className="flex items-center gap-1 w-fit">
                      <ShieldCheck className="w-3 h-3" />
                      管理员
                    </Badge>
                  ) : (
                    <Badge variant="gray" className="flex items-center gap-1 w-fit">
                      <Shield className="w-3 h-3" />
                      普通用户
                    </Badge>
                  )}
                </td>
                <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                  {formatDate(user.created_at)}
                </td>
                <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                  {formatDate(user.activated_at)}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center justify-end gap-2">
                    {!user.is_active && (
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => handleActivateUser(user.id)}
                        disabled={actionLoading === user.id}
                        className="flex items-center gap-1"
                      >
                        {actionLoading === user.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <UserCheck className="w-3 h-3" />
                        )}
                        激活
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant={user.is_admin ? 'danger' : 'secondary'}
                      onClick={() => handleToggleAdmin(user.id, user.is_admin)}
                      disabled={actionLoading === user.id}
                      className="flex items-center gap-1"
                    >
                      {actionLoading === user.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : user.is_admin ? (
                        <UserX className="w-3 h-3" />
                      ) : (
                        <Shield className="w-3 h-3" />
                      )}
                      {user.is_admin ? '取消管理员' : '设为管理员'}
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleDeleteClick(user.id, user.email)}
                      disabled={actionLoading === user.id}
                    >
                      {actionLoading === user.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Trash2 className="w-3 h-3" />
                      )}
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="确认删除用户"
        message={
          <div>
            <p>确定要删除用户 <strong>{deleteConfirm.userEmail}</strong> 吗？</p>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              该用户的所有音频将被转移到您的账户下。此操作无法撤销。
            </p>
          </div>
        }
        confirmLabel="删除"
        cancelLabel="取消"
        variant="danger"
      />
    </div>
  )
}
