import { useAtom } from 'jotai'
import { ChevronDown } from 'lucide-react'
import { channelFilterAtom, channelsAtom } from '../../atoms/channels'
import { Channel } from './ChannelBadge'

/**
 * Channel filter dropdown for transcription list.
 *
 * Provides filtering options:
 * - All: Show all transcriptions (personal + channels)
 * - Personal: Show only my own content
 * - Channel 1, Channel 2, ...: Filter by specific channel
 */
export function ChannelFilter() {
  const [channels] = useAtom(channelsAtom)
  const [filter, setFilter] = useAtom(channelFilterAtom)

  const getFilterLabel = (): string => {
    if (filter === null) return '全部内容'
    if (filter === 'personal') return '个人内容'

    const channel = channels.find((c) => c.id === filter)
    return channel?.name || filter
  }

  const handleFilterChange = (value: string | null) => {
    setFilter(value)
  }

  return (
    <div className="relative inline-block text-left">
      <div className="flex items-center gap-2">
        <label htmlFor="channel-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">
          频道筛选:
        </label>
        <div className="relative">
          <select
            id="channel-filter"
            value={filter ?? 'all'}
            onChange={(e) => {
              const value = e.target.value
              handleFilterChange(value === 'all' ? null : value === 'personal' ? 'personal' : value)
            }}
            className="appearance-none bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 text-sm rounded-lg px-4 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer"
          >
            <option value="all">全部内容</option>
            <option value="personal">个人内容</option>
            {channels.map((channel) => (
              <option key={channel.id} value={channel.id}>
                {channel.name}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2">
            <ChevronDown className="h-4 w-4 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Active filter display */}
      {filter && filter !== 'all' && (
        <div className="mt-2 flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">当前筛选:</span>
          <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
            {getFilterLabel()}
          </span>
          <button
            onClick={() => handleFilterChange(null)}
            className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 underline"
          >
            清除筛选
          </button>
        </div>
      )}
    </div>
  )
}
