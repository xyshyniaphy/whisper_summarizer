import { Badge } from '../ui/Badge'

export interface Channel {
  id: string
  name: string
  description?: string
}

interface ChannelBadgeProps {
  channels: Channel[]
  isPersonal?: boolean
  maxDisplay?: number
  onClick?: () => void
  className?: string
}

/**
 * Display channel badges for transcription items.
 *
 * - Single channel: Show badge with channel name
 * - Multiple channels: Show "N channels" badge or comma-separated names
 * - Personal (no channels): Show "Personal" badge or no badge
 * - Clickable: Optional onClick handler for filtering
 */
export function ChannelBadge({
  channels,
  isPersonal = false,
  maxDisplay = 2,
  onClick,
  className = ''
}: ChannelBadgeProps) {
  // Personal content (no channel assignments)
  if (isPersonal || channels.length === 0) {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 ${className}`}
      >
        个人
      </span>
    )
  }

  // Single channel
  if (channels.length === 1) {
    return (
      <button
        onClick={onClick}
        className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors ${onClick ? 'cursor-pointer' : ''} ${className}`}
        title={channels[0].description || channels[0].name}
      >
        {channels[0].name}
      </button>
    )
  }

  // Multiple channels
  if (channels.length <= maxDisplay) {
    return (
      <div className={`inline-flex items-center gap-1 flex-wrap ${className}`}>
        {channels.map((channel) => (
          <button
            key={channel.id}
            onClick={onClick}
            className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors ${onClick ? 'cursor-pointer' : ''}`}
            title={channel.description || channel.name}
          >
            {channel.name}
          </button>
        ))}
      </div>
    )
  }

  // Too many channels - show count
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors ${onClick ? 'cursor-pointer' : ''} ${className}`}
      title={channels.map(c => c.name).join(', ')}
    >
      {channels.length} 个频道
    </button>
  )
}
