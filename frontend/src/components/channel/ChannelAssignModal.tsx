import { useState, useEffect } from 'react'
import { X, Check, Search } from 'lucide-react'
import { useAtom } from 'jotai'
import { channelsAtom } from '../../atoms/channels'
import { adminApi } from '../../services/api'
import { Channel } from './ChannelBadge'
import { Modal } from '../ui/Modal'

interface ChannelAssignModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (channelIds: string[]) => Promise<void>
  transcriptionId: string
  currentChannelIds: string[]
  loading?: boolean
}

/**
 * Modal for assigning transcriptions to multiple channels.
 *
 * Features:
 * - Multi-select checkboxes for channels
 * - Search/filter channels by name
 * - Show current selections
 * - Save/Cancel buttons
 * - Loading state during save
 */
export function ChannelAssignModal({
  isOpen,
  onClose,
  onConfirm,
  transcriptionId,
  currentChannelIds,
  loading = false
}: ChannelAssignModalProps) {
  const [channels, setChannels] = useState<Channel[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(currentChannelIds))
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load available channels
  useEffect(() => {
    if (isOpen) {
      setError(null)
      loadChannels()
    }
  }, [isOpen])

  // Reset selections when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedIds(new Set(currentChannelIds))
      setError(null)
    }
  }, [isOpen, currentChannelIds])

  const loadChannels = async () => {
    setIsLoading(true)
    try {
      const data = await adminApi.listChannels()
      setChannels(data)
    } catch (error) {
      console.error('Failed to load channels:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const toggleChannel = (channelId: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(channelId)) {
      newSelected.delete(channelId)
    } else {
      newSelected.add(channelId)
    }
    setSelectedIds(newSelected)
  }

  const toggleAll = () => {
    const filteredIds = getFilteredChannels().map((c) => c.id)
    if (filteredIds.every((id) => selectedIds.has(id))) {
      // Deselect all filtered
      const newSelected = new Set(selectedIds)
      filteredIds.forEach((id) => newSelected.delete(id))
      setSelectedIds(newSelected)
    } else {
      // Select all filtered
      const newSelected = new Set(selectedIds)
      filteredIds.forEach((id) => newSelected.add(id))
      setSelectedIds(newSelected)
    }
  }

  const getFilteredChannels = (): Channel[] => {
    if (!searchQuery) return channels

    const query = searchQuery.toLowerCase()
    return channels.filter((channel) =>
      channel.name.toLowerCase().includes(query) ||
      (channel.description && channel.description.toLowerCase().includes(query))
    )
  }

  const handleConfirm = async () => {
    setError(null)
    setIsSaving(true)
    try {
      await onConfirm(Array.from(selectedIds))
      onClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '分配频道失败，请稍后再试'
      setError(errorMessage)
      console.error('Failed to assign channels:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const filteredChannels = getFilteredChannels()
  const allFilteredSelected = filteredChannels.length > 0 &&
    filteredChannels.every((c) => selectedIds.has(c.id))

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="分配到频道">
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          <span className="ml-3 text-gray-600 dark:text-gray-400">加载频道列表...</span>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Error message */}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          )}

          {/* Search input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="搜索频道名称..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Select All / Deselect All */}
          {filteredChannels.length > 0 && (
            <button
              onClick={toggleAll}
              className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
            >
              <Check className="w-4 h-4" />
              {allFilteredSelected ? '取消选择所有' : '选择所有'}
            </button>
          )}

          {/* Channel list */}
          <div className="max-h-64 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg divide-y divide-gray-200 dark:divide-gray-700">
            {filteredChannels.length === 0 ? (
              <div className="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">
                {searchQuery ? '未找到匹配的频道' : '暂无可用频道'}
              </div>
            ) : (
              filteredChannels.map((channel) => {
                const isSelected = selectedIds.has(channel.id)
                return (
                  <label
                    key={channel.id}
                    className={`flex items-start p-3 cursor-pointer transition-colors ${
                      isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleChannel(channel.id)}
                      className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="ml-3 flex-1">
                      <div className="font-medium text-gray-900 dark:text-gray-100">
                        {channel.name}
                      </div>
                      {channel.description && (
                        <div className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                          {channel.description}
                        </div>
                      )}
                    </div>
                  </label>
                )
              })
            )}
          </div>

          {/* Selection summary */}
          {selectedIds.size > 0 && (
            <div className="text-sm text-gray-600 dark:text-gray-400">
              已选择 {selectedIds.size} 个频道
            </div>
          )}

          {/* Action buttons */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={onClose}
              disabled={isSaving}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              取消
            </button>
            <button
              onClick={handleConfirm}
              disabled={isSaving}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSaving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  保存中...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  保存
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}
