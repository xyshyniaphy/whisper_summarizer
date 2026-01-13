/**
 * AudioPlayer Component
 *
 * Audio player with SRT segment navigation for shared transcriptions.
 * Features:
 * - Audio playback controls (play/pause, seek bar)
 * - Segment navigation (click to seek)
 * - Current segment highlighting
 * - Expand/collapse for segment text
 * - Fixed position at bottom of viewport
 */

import { useState, useRef, useEffect } from 'react'
import { Play, Pause, Maximize2, Minimize2 } from 'lucide-react'
import { cn } from '../utils/cn'

export interface Segment {
  start: number
  end: number
  text: string
}

interface AudioPlayerProps {
  audioUrl: string
  segments: Segment[]
  onSeek: (time: number) => void
}

export function AudioPlayer({ audioUrl, segments, onSeek }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isExpanded, setIsExpanded] = useState(false)
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState<number | null>(null)
  const [audioError, setAudioError] = useState<string | null>(null)

  // Handle play/pause toggle with async state update
  const togglePlayPause = async () => {
    if (!audioRef.current) return

    try {
      if (isPlaying) {
        audioRef.current.pause()
        setIsPlaying(false)
      } else {
        await audioRef.current.play()
        setIsPlaying(true)
      }
    } catch (error) {
      // Handle autoplay policies or other play errors
      console.error('Failed to toggle playback:', error)
      setIsPlaying(false)
    }
  }

  // Handle seek bar change
  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value)
    if (audioRef.current) {
      audioRef.current.currentTime = time
      setCurrentTime(time)
    }
  }

  // Handle segment click
  const handleSegmentClick = (segment: Segment) => {
    if (audioRef.current) {
      audioRef.current.currentTime = segment.start
      setCurrentTime(segment.start)
      onSeek(segment.start)
    }
  }

  // Handle audio load errors
  const handleAudioError = () => {
    setAudioError('音频加载失败，请稍后重试')
    console.error('Audio failed to load')
  }

  // Update current time
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleTimeUpdate = () => {
      const time = audio.currentTime
      setCurrentTime(time)

      // Find current segment
      const index = segments.findIndex(
        (seg) => time >= seg.start && time < seg.end
      )
      setCurrentSegmentIndex(index >= 0 ? index : null)
    }

    const handleLoadedMetadata = () => {
      setDuration(audio.duration)
      setAudioError(null) // Clear error on successful load
    }

    const handlePlay = () => setIsPlaying(true)
    const handlePause = () => setIsPlaying(false)
    const handleEnded = () => setIsPlaying(false)

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('loadedmetadata', handleLoadedMetadata)
    audio.addEventListener('play', handlePlay)
    audio.addEventListener('pause', handlePause)
    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('error', handleAudioError)

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
      audio.removeEventListener('play', handlePlay)
      audio.removeEventListener('pause', handlePause)
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('error', handleAudioError)
    }
  }, [segments])

  // Format time as MM:SS
  const formatTime = (time: number): string => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }

  return (
    <div
      data-testid="audio-player-container"
      className={cn(
        'fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 shadow-lg transition-all duration-300 z-50',
        isExpanded ? 'h-32' : 'h-16'
      )}
      role="region"
      aria-label="音频播放器"
    >
      <audio
        ref={audioRef}
        data-testid="audio-element"
        src={audioUrl}
        className="hidden"
        onError={handleAudioError}
      />

      {/* Error message */}
      {audioError && (
        <div className="px-4 py-2 bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100 text-sm">
          {audioError}
        </div>
      )}

      {/* Compact controls */}
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-4 flex-1">
          {/* Play/Pause button */}
          <button
            data-testid="play-button"
            onClick={togglePlayPause}
            aria-label={isPlaying ? '暂停' : '播放'}
            className={cn(
              'p-2 rounded-lg transition-colors',
              isPlaying ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            )}
          >
            {isPlaying ? <Pause size={20} /> : <Play size={20} />}
          </button>

          {/* Seek bar */}
          <div className="flex-1 flex items-center gap-2">
            <span
              className="text-sm text-gray-600 dark:text-gray-400 w-20 text-right"
              aria-label={`当前时间 ${formatTime(currentTime)}`}
            >
              {formatTime(currentTime)}
            </span>
            <input
              type="range"
              min="0"
              max={duration || 0}
              step="0.1"
              value={currentTime}
              onChange={handleSeek}
              aria-label="进度条"
              aria-valuemin={0}
              aria-valuemax={duration}
              aria-valuenow={currentTime}
              aria-valuetext={formatTime(currentTime)}
              className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
            <span
              className="text-sm text-gray-600 dark:text-gray-400 w-20"
              aria-label={`总时长 ${formatTime(duration)}`}
            >
              {formatTime(duration)}
            </span>
          </div>
        </div>

        {/* Expand/Collapse button */}
        <button
          data-testid="expand-button"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-label={isExpanded ? '收起段落' : '展开段落'}
          aria-expanded={isExpanded}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          {isExpanded ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
        </button>
      </div>

      {/* Expanded view: Segments */}
      {isExpanded && (
        <div
          className="px-4 pb-2 overflow-y-auto"
          style={{ maxHeight: 'calc(100% - 64px)' }}
        >
          <div
            className="flex gap-2 overflow-x-auto"
            role="list"
            aria-label="转录段落"
          >
            {segments.map((segment, index) => (
              <button
                key={index}
                data-testid={`segment-${index}`}
                onClick={() => handleSegmentClick(segment)}
                role="listitem"
                aria-label={`跳转到第 ${index + 1} 段: ${segment.text}`}
                aria-current={currentSegmentIndex === index ? 'true' : undefined}
                className={cn(
                  'flex-shrink-0 px-3 py-1 rounded-lg text-sm transition-colors',
                  currentSegmentIndex === index
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-900 dark:text-blue-100'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                )}
              >
                {segment.text}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
