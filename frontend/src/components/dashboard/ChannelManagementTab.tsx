/**
 * Channel Management Tab for Admin Dashboard
 * Allows admins to create, edit, delete channels and manage members
 */

import { useState, useEffect } from 'react'
import { adminApi } from '../../services/api'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Modal } from '../ui/Modal'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { Loader2, Plus, Edit2, Trash2, UserMinus, Users } from 'lucide-react'

interface Channel {
  id: string
  name: string
  description?: string
  created_by?: string
  created_at: string
  updated_at: string
  member_count?: number
}

interface ChannelMember {
  id: string
  email: string
  is_active: boolean
  is_admin: boolean
}

interface ChannelFormData {
  name: string
  description: string
}

interface ModalState {
  isOpen: boolean
  mode: 'create' | 'edit'
  channelId: string | null
  initialData: ChannelFormData
}

interface MembersModalState {
  isOpen: boolean
  channelId: string | null
  channelName: string
}

interface DeleteConfirmState {
  isOpen: boolean
  channelId: string | null
  channelName: string | null
}

export function ChannelManagementTab() {
  const [channels, setChannels] = useState<Channel[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [modal, setModal] = useState<ModalState>({
    isOpen: false,
    mode: 'create',
    channelId: null,
    initialData: { name: '', description: '' },
  })
  const [membersModal, setMembersModal] = useState<MembersModalState>({
    isOpen: false,
    channelId: null,
    channelName: '',
  })
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirmState>({
    isOpen: false,
    channelId: null,
    channelName: null,
  })
  const [availableUsers, setAvailableUsers] = useState<ChannelMember[]>([])
  const [selectedUserId, setSelectedUserId] = useState<string>('')
  const [currentMembers, setCurrentMembers] = useState<ChannelMember[]>([])
  const [membersLoading, setMembersLoading] = useState(false)

  const fetchChannels = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminApi.listChannels()
      setChannels(data)
    } catch (err) {
      console.error('Error fetching channels:', err)
      setError('加载频道列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchChannels()
  }, [])

  const fetchMembers = async (channelId: string) => {
    try {
      const data = await adminApi.getChannelDetail(channelId)
      return data.members || []
    } catch (err) {
      console.error('Error fetching members:', err)
      return []
    }
  }

  const fetchAvailableUsers = async () => {
    try {
      const users = await adminApi.listUsers()
      setAvailableUsers(users.filter(u => u.is_active))
    } catch (err) {
      console.error('Error fetching users:', err)
    }
  }

  const handleCreateChannel = () => {
    setModal({
      isOpen: true,
      mode: 'create',
      channelId: null,
      initialData: { name: '', description: '' },
    })
  }

  const handleEditChannel = async (channelId: string) => {
    setActionLoading(channelId)
    try {
      const data = await adminApi.getChannelDetail(channelId)
      setModal({
        isOpen: true,
        mode: 'edit',
        channelId,
        initialData: { name: data.name, description: data.description || '' },
      })
    } catch (err) {
      console.error('Error fetching channel:', err)
      alert('加载频道详情失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleManageMembers = async (channelId: string, channelName: string) => {
    setActionLoading(channelId)
    setMembersModal({ isOpen: true, channelId, channelName })
    await fetchAvailableUsers()
    // Fetch current members
    setMembersLoading(true)
    try {
      const members = await fetchMembers(channelId)
      setCurrentMembers(members)
    } catch (err) {
      console.error('Error fetching members:', err)
      setCurrentMembers([])
    } finally {
      setMembersLoading(false)
    }
    setActionLoading(null)
  }

  const handleDeleteClick = (channelId: string, channelName: string) => {
    setDeleteConfirm({ isOpen: true, channelId, channelName })
  }

  const handleModalClose = () => {
    setModal({
      isOpen: false,
      mode: 'create',
      channelId: null,
      initialData: { name: '', description: '' },
    })
  }

  const handleModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const { name, description } = modal.initialData

    if (!name.trim()) {
      alert('请输入频道名称')
      return
    }

    setActionLoading(modal.channelId || 'create')

    try {
      if (modal.mode === 'create') {
        await adminApi.createChannel({ name: name.trim(), description: description.trim() || undefined })
      } else {
        await adminApi.updateChannel(modal.channelId!, {
          name: name.trim(),
          description: description.trim() || undefined,
        })
      }
      handleModalClose()
      await fetchChannels()
    } catch (err) {
      console.error('Error saving channel:', err)
      alert('保存频道失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleAddMember = async () => {
    if (!selectedUserId || !membersModal.channelId) return

    setActionLoading(`add-${selectedUserId}`)
    try {
      await adminApi.assignUserToChannel(membersModal.channelId, selectedUserId)
      setSelectedUserId('')
      await fetchAvailableUsers()
      // Refresh members list
      const members = await fetchMembers(membersModal.channelId)
      setCurrentMembers(members)
    } catch (err) {
      console.error('Error adding member:', err)
      alert('添加成员失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleRemoveMember = async (userId: string) => {
    if (!membersModal.channelId) return

    setActionLoading(`remove-${userId}`)
    try {
      await adminApi.removeUserFromChannel(membersModal.channelId, userId)
      // Refresh members list
      const members = await fetchMembers(membersModal.channelId)
      setCurrentMembers(members)
      await fetchAvailableUsers()
    } catch (err) {
      console.error('Error removing member:', err)
      alert('移除成员失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleteConfirm.channelId) return

    setActionLoading(deleteConfirm.channelId)
    setDeleteConfirm({ isOpen: false, channelId: null, channelName: null })

    try {
      await adminApi.deleteChannel(deleteConfirm.channelId)
      await fetchChannels()
    } catch (err) {
      console.error('Error deleting channel:', err)
      alert('删除频道失败: ' + (err as Error).message)
    } finally {
      setActionLoading(null)
    }
  }

  const formatDate = (dateString: string) => {
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
        <Button onClick={fetchChannels} className="mt-4">
          重试
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with create button */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            频道列表
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            共 {channels.length} 个频道
          </p>
        </div>
        <Button onClick={handleCreateChannel} className="flex items-center gap-2">
          <Plus className="w-4 h-4" />
          创建频道
        </Button>
      </div>

      {/* Channels table */}
      <div className="overflow-x-auto">
        <table className="w-full" data-testid="channel-list">
          <thead>
            <tr className="border-b dark:border-gray-700">
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">频道名称</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">描述</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">成员数量</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">更新时间</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">操作</th>
            </tr>
          </thead>
          <tbody>
            {channels.map((channel) => (
              <tr key={channel.id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="py-3 px-4">
                  <span className="font-medium text-gray-900 dark:text-gray-100">{channel.name}</span>
                </td>
                <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                  {channel.description || '-'}
                </td>
                <td className="py-3 px-4">
                  <Badge variant="info" className="flex items-center gap-1 w-fit">
                    <Users className="w-3 h-3" />
                    {channel.member_count || 0}
                  </Badge>
                </td>
                <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                  {formatDate(channel.updated_at)}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleManageMembers(channel.id, channel.name)}
                      disabled={actionLoading === channel.id}
                    >
                      {actionLoading === channel.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Users className="w-3 h-3" />
                      )}
                      成员
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleEditChannel(channel.id)}
                      disabled={actionLoading === channel.id}
                    >
                      <Edit2 className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleDeleteClick(channel.id, channel.name)}
                      disabled={actionLoading === channel.id}
                      data-testid="delete-channel-button"
                    >
                      {actionLoading === channel.id ? (
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

      {/* Create/Edit modal */}
      <Modal
        isOpen={modal.isOpen}
        onClose={handleModalClose}
        title={modal.mode === 'create' ? '创建频道' : '编辑频道'}
      >
        <form onSubmit={handleModalSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              频道名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={modal.initialData.name}
              onChange={(e) => setModal({
                ...modal,
                initialData: { ...modal.initialData, name: e.target.value }
              })}
              className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="输入频道名称"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              描述
            </label>
            <textarea
              value={modal.initialData.description}
              onChange={(e) => setModal({
                ...modal,
                initialData: { ...modal.initialData, description: e.target.value }
              })}
              className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              rows={3}
              placeholder="输入频道描述（可选）"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={handleModalClose}>
              取消
            </Button>
            <Button type="submit" disabled={actionLoading === (modal.channelId || 'create')}>
              {actionLoading === (modal.channelId || 'create') ? (
                <>
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                  保存中...
                </>
              ) : (
                '保存'
              )}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Members management modal */}
      <Modal
        isOpen={membersModal.isOpen}
        onClose={() => setMembersModal({ isOpen: false, channelId: null, channelName: '' })}
        title={`管理成员 - ${membersModal.channelName}`}
      >
        <div className="space-y-4">
          {/* Add member */}
          <div className="flex gap-2">
            <select
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              className="flex-1 px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="">选择用户添加...</option>
              {availableUsers
                .filter(user => !currentMembers.some(member => member.id === user.id))
                .map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.email} {user.is_admin ? '(管理员)' : ''}
                  </option>
                ))}
            </select>
            <Button
              type="button"
              onClick={handleAddMember}
              disabled={!selectedUserId || actionLoading === `add-${selectedUserId}`}
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>

          {/* Current members list */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              当前成员 ({currentMembers.length})
            </h4>
            {membersLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-primary-600 animate-spin" />
              </div>
            ) : currentMembers.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
                暂无成员
              </p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {currentMembers.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-900 dark:text-gray-100">
                        {member.email}
                      </span>
                      {member.is_admin && (
                        <Badge variant="info">管理员</Badge>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleRemoveMember(member.id)}
                      disabled={actionLoading === `remove-${member.id}`}
                    >
                      {actionLoading === `remove-${member.id}` ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <UserMinus className="w-3 h-3" />
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setMembersModal({ isOpen: false, channelId: null, channelName: '' })}
            >
              关闭
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        onClose={() => setDeleteConfirm({ isOpen: false, channelId: null, channelName: null })}
        onConfirm={handleDeleteConfirm}
        title="确认删除频道"
        message={
          <div>
            <p>确定要删除频道 <strong>{deleteConfirm.channelName}</strong> 吗？</p>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              此操作将解除该频道与所有音频的关联，但不会删除音频本身。此操作无法撤销。
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
