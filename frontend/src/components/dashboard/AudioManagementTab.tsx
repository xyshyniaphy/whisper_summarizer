/**
 * Audio Management Tab for Admin Dashboard
 * Allows admins to view all audio files and assign them to channels
 */

import { useState, useEffect } from 'react'
import { adminApi } from '../../services/api'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Modal } from '../ui/Modal'
import { Loader2, FolderOpen, Music, Save } from 'lucide-react'

interface AudioItem {
  id: string
  file_name: string
  created_at: string
  user_id: string
  user_email: string
  channels: Array<{
    id: string
    name: string
  }>
}

interface Channel {
  id: string
  name: string
  description?: string
}

interface AssignModalState {
  isOpen: boolean
  audioId: string | null
  audioName: string
  assignedChannelIds: string[]
}

export function AudioManagementTab() {
  const [audioList, setAudioList] = useState<AudioItem[]>([])
  const [channels, setChannels] = useState<Channel[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [assignModal, setAssignModal] = useState<AssignModalState>({
    isOpen: false,
    audioId: null,
    audioName: '',
    assignedChannelIds: [],
  })

  const fetchAudioList = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminApi.listAllAudio()
      setAudioList(data)
    } catch (err) {
      console.error('Error fetching audio list:', err)
      setError('加载音频列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchChannels = async () => {
    try {
      const data = await adminApi.listChannels()
      setChannels(data)
    } catch (err) {
      console.error('Error fetching channels:', err)
    }
  }

  useEffect(() => {
    fetchAudioList()
    fetchChannels()
  }, [])

  const handleAssignChannels = async (audioId: string, audioName: string, currentChannels: string[]) => {
    setActionLoading(audioId)
    try {
      const data = await adminApi.getAudioChannels(audioId)
      setAssignModal({
        isOpen: true,
        audioId,
        audioName,
        assignedChannelIds: data.map((c: any) => c.id),
      })
    } catch (err) {
      console.error('Error fetching audio channels:', err)
      alert('加载频道信息失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleAssignModalClose = () => {
    setAssignModal({
      isOpen: false,
      audioId: null,
      audioName: '',
      assignedChannelIds: [],
    })
  }

  const handleToggleChannel = (channelId: string) => {
    setAssignModal({
      ...assignModal,
      assignedChannelIds: assignModal.assignedChannelIds.includes(channelId)
        ? assignModal.assignedChannelIds.filter(id => id !== channelId)
        : [...assignModal.assignedChannelIds, channelId],
    })
  }

  const handleSaveAssignments = async () => {
    if (!assignModal.audioId) return

    setActionLoading(`assign-${assignModal.audioId}`)
    try {
      await adminApi.assignAudioToChannels(assignModal.audioId, assignModal.assignedChannelIds)
      handleAssignModalClose()
      await fetchAudioList()
    } catch (err) {
      console.error('Error assigning channels:', err)
      alert('分配频道失败')
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
        <Button onClick={fetchAudioList} className="mt-4">
          重试
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          音频列表
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          共 {audioList.length} 个音频文件
        </p>
      </div>

      {/* Audio table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b dark:border-gray-700">
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">文件名</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">所有者</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">分配频道</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">创建时间</th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">操作</th>
            </tr>
          </thead>
          <tbody>
            {audioList.map((audio) => (
              <tr key={audio.id} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <Music className="w-4 h-4 text-gray-400" />
                    <span className="font-medium text-gray-900 dark:text-gray-100 truncate max-w-xs">
                      {audio.file_name}
                    </span>
                  </div>
                </td>
                <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                  {audio.user_email}
                </td>
                <td className="py-3 px-4">
                  {audio.channels.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {audio.channels.map((channel) => (
                        <Badge key={channel.id} variant="info" className="text-xs">
                          {channel.name}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400 dark:text-gray-600">未分配</span>
                  )}
                </td>
                <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                  {formatDate(audio.created_at)}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleAssignChannels(audio.id, audio.file_name, audio.channels.map(c => c.id))}
                      disabled={actionLoading === audio.id}
                      className="flex items-center gap-1"
                    >
                      {actionLoading === audio.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <FolderOpen className="w-3 h-3" />
                      )}
                      分配频道
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Assign channels modal */}
      <Modal
        isOpen={assignModal.isOpen}
        onClose={handleAssignModalClose}
        title={`分配频道 - ${assignModal.audioName}`}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              选择要分配的频道
            </label>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {channels.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">暂无可用频道</p>
              ) : (
                channels.map((channel) => (
                  <label
                    key={channel.id}
                    className="flex items-center gap-3 p-3 rounded-lg border dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={assignModal.assignedChannelIds.includes(channel.id)}
                      onChange={() => handleToggleChannel(channel.id)}
                      className="w-4 h-4 text-primary-600 rounded"
                    />
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 dark:text-gray-100">{channel.name}</p>
                      {channel.description && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">{channel.description}</p>
                      )}
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>

          <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
            <span>
              已选择 {assignModal.assignedChannelIds.length} 个频道
            </span>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t dark:border-gray-700">
            <Button variant="ghost" onClick={handleAssignModalClose}>
              取消
            </Button>
            <Button
              onClick={handleSaveAssignments}
              disabled={actionLoading === `assign-${assignModal.audioId}`}
              className="flex items-center gap-1"
            >
              {actionLoading === `assign-${assignModal.audioId}` ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  保存
                </>
              )}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
