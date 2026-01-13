import { useEffect, useRef } from 'react'
import { Clock } from 'lucide-react'
import { cn } from '../utils/cn'

// Export Segment interface for reuse
export interface Segment {
  start: number
  end: number
  text: string
}

interface SrtListProps {
  segments: Segment[]
  currentTime: number
  onSeek: (time: number) => void
}

/**
 * Formats seconds to MM:SS format
 */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

/**
 * Finds the current segment index based on currentTime
 */
function findCurrentSegmentIndex(segments: Segment[], currentTime: number): number {
  if (segments.length === 0) return -1
  return segments.findIndex(seg => currentTime >= seg.start && currentTime < seg.end)
}

/**
 * SrtList Component
 *
 * Displays a list of transcription segments with:
 * - Timestamp display (MM:SS format)
 * - Current segment highlighting
 * - Click to seek functionality
 * - Auto-scroll to current segment
 */
export default function SrtList({ segments, currentTime, onSeek }: SrtListProps) {
  const currentSegmentRef = useRef<HTMLDivElement>(null)
  const prevIndexRef = useRef<number>(-1)
  const currentIndex = findCurrentSegmentIndex(segments, currentTime)

  // Auto-scroll current segment into view when it changes
  useEffect(() => {
    if (currentIndex !== prevIndexRef.current && currentIndex >= 0) {
      prevIndexRef.current = currentIndex
      currentSegmentRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      })
    }
  }, [currentIndex])

  // Handle empty state
  if (segments.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-600">
        <p>暂无字幕数据</p>
      </div>
    )
  }

  return (
    <div
      role="list"
      className="h-full overflow-y-auto"
      aria-label="字幕列表"
    >
      {segments.map((segment, index) => {
        const isCurrent = index === currentIndex

        return (
          <div
            key={index}
            ref={isCurrent ? currentSegmentRef : null}
            role="listitem"
            data-segment-index={index}
            data-current={isCurrent}
            tabIndex={0}
            onClick={() => onSeek(segment.start)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onSeek(segment.start)
              }
            }}
            className={cn(
              'flex gap-3 p-3 sm:p-4 cursor-pointer transition-all duration-200 min-h-[48px]',
              'hover:bg-gray-100 dark:hover:bg-gray-700',
              isCurrent && 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 dark:border-blue-400'
            )}
            aria-label={`${formatTime(segment.start)} - ${segment.text}`}
            aria-current={isCurrent ? 'true' : undefined}
          >
            {/* Timestamp */}
            <div className="flex-shrink-0">
              <div className={cn(
                'flex items-center gap-1.5 text-sm font-mono',
                isCurrent ? 'text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400'
              )}>
                <Clock className="w-3 h-3 sm:w-4 sm:h-4" />
                <time dateTime={`PT${Math.floor(segment.start)}S`}>
                  {formatTime(segment.start)}
                </time>
              </div>
            </div>

            {/* Segment text */}
            <div className="flex-1 text-sm sm:text-base leading-relaxed text-gray-800 dark:text-gray-200">
              {segment.text}
            </div>

            {/* Current segment indicator */}
            {isCurrent && (
              <div className="flex-shrink-0">
                <div className="w-2 h-2 sm:w-3 sm:h-3 bg-blue-500 rounded-full animate-pulse" />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
