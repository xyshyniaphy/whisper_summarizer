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
  onTimeUpdate?: (time: number) => void  // Called during playback to sync parent state
  currentTime?: number  // External control for seek (from SrtList clicks)
}

export function AudioPlayer({ audioUrl, segments, onSeek, onTimeUpdate, currentTime: externalCurrentTime }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [internalCurrentTime, setInternalCurrentTime] = useState(0)
  // Use external time if provided, otherwise use internal state
  const currentTime = externalCurrentTime ?? internalCurrentTime
  const [duration, setDuration] = useState(0)
  const [isExpanded, setIsExpanded] = useState(false)
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState<number | null>(null)
  const [audioError, setAudioError] = useState<string | null>(null)
  const lastSeekTimeRef = useRef<number>(0)

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
      setInternalCurrentTime(time)
      onSeek(time)
    }
  }

  // Handle segment click
  const handleSegmentClick = (segment: Segment) => {
    if (audioRef.current) {
      audioRef.current.currentTime = segment.start
      setInternalCurrentTime(segment.start)
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
      setInternalCurrentTime(time)

      // Notify parent of time update for segment highlighting
      if (onTimeUpdate) {
        onTimeUpdate(time)
      }

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

  // Handle external seek requests (from SrtList clicks)
  useEffect(() => {
    // Only handle external seeks when the time has changed significantly
    if (externalCurrentTime !== undefined && Math.abs(externalCurrentTime - lastSeekTimeRef.current) > 0.1) {
      if (audioRef.current) {
        // Preserve playing state during seek
        const wasPlaying = !audioRef.current.paused
        audioRef.current.currentTime = externalCurrentTime
        lastSeekTimeRef.current = externalCurrentTime
        // Ensure audio continues playing if it was playing before seek
        if (wasPlaying && audioRef.current.paused) {
          audioRef.current.play().catch(err => {
            console.debug('Autoplay prevented:', err)
          })
        }
      }
    }
  }, [externalCurrentTime])

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
        isExpanded ? 'h-24 sm:h-32' : 'h-16 sm:h-20'
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
      <div className="flex items-center justify-between px-3 sm:px-4 py-2">
        <div className="flex items-center gap-2 sm:gap-4 flex-1">
          {/* Play/Pause button */}
          <button
            data-testid="play-button"
            onClick={togglePlayPause}
            aria-label={isPlaying ? '暂停' : '播放'}
            className={cn(
              'p-2 rounded-lg transition-colors w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center',
              isPlaying ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            )}
          >
            {isPlaying ? <Pause className="w-5 h-5 sm:w-6 sm:h-6" /> : <Play className="w-5 h-5 sm:w-6 sm:h-6" />}
          </button>

          {/* Seek bar */}
          <div className="flex-1 flex items-center gap-2">
            <span
              className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 w-16 sm:w-20 text-right"
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
              className="flex-1 h-2 sm:h-3 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
            <span
              className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 w-16 sm:w-20"
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
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center"
        >
          {isExpanded ? <Minimize2 className="w-5 h-5 sm:w-6 sm:h-6" /> : <Maximize2 className="w-5 h-5 sm:w-6 sm:h-6" />}
        </button>
      </div>

      {/* Expanded view: Segments */}
      {isExpanded && (
        <div
          className="px-3 sm:px-4 pb-2 overflow-y-auto"
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
                  'flex-shrink-0 px-3 py-1 rounded-lg text-xs sm:text-sm transition-colors',
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
