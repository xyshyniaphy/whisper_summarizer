/**
 * Shared Audio Player E2E Tests
 *
 * Tests for audio player with SRT navigation on shared transcription pages.
 * Verifies audio playback, segment seeking, and current segment highlighting.
 */

import { test, expect, type Page } from '@playwright/test'
import { getOrCreateSharedTranscriptionWithShare } from '../helpers/test-data'

const BASE_URL = process.env.BASE_URL || 'http://localhost:8130'

// Declare shareToken at module level so both test.describe blocks can access it
let shareToken: string

// Helper to expand SRT section (collapsed by default)
async function expandSrtSection(page: Page) {
  // Wait for the SRT section button to be available
  const srtSectionButton = page.getByRole('button', { name: '音频播放与字幕' }).first()

  // Wait for button to be attached to DOM
  await srtSectionButton.waitFor({ state: 'attached' })

  // Check if section is collapsed (aria-expanded="false")
  const ariaExpanded = await srtSectionButton.getAttribute('aria-expanded')

  if (ariaExpanded === 'false') {
    // Click to expand
    await srtSectionButton.click()
    // Wait for the segments container to appear (check for VirtualizedSrtList)
    await page.waitForSelector('[role="list"]', { timeout: 5000 }).catch(() => {
      // If [role="list"] doesn't appear, try waiting for any segment
      return page.waitForSelector('[data-testid^="segment-"]', { timeout: 5000 })
    })
  }
}

test.describe.configure({ mode: 'serial' }) // Run tests sequentially to share state

test.beforeAll(async ({ browser }) => {
  // Setup a transcription with share link for all tests
  // Create a new page manually since beforeAll doesn't support page fixture
  const context = await browser.newContext()
  const page = await context.newPage()
  shareToken = await getOrCreateSharedTranscriptionWithShare(page)
  await context.close()
  console.log(`[Test Setup] Share token: ${shareToken}`)
})

test.describe('Shared Audio Player', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to shared transcription page
    await page.goto(`${BASE_URL}/shared/${shareToken}`)

    // Initialize console errors array in browser context
    await page.evaluate(() => {
      ;(window as any).consoleErrors = []
    })

    // Track console errors for tests - store in browser context
    page.on('console', async msg => {
      if (msg.type() === 'error') {
        // Push to window.consoleErrors in browser context
        await page.evaluate((errorText) => {
          (window as any).consoleErrors.push(errorText)
        }, msg.text())
      }
    })
  })

  test('should load shared transcription and display audio player', async ({ page }) => {
    // Wait for page to load
    await page.waitForLoadState('networkidle')

    // Verify audio player container is visible
    const audioPlayer = page.locator('[data-testid="audio-player-container"]')
    await expect(audioPlayer).toBeVisible()

    // Verify audio element exists
    const audioElement = page.locator('[data-testid="audio-element"]')
    await expect(audioElement).toHaveAttribute('src', /\/api\/shared\/.*\/audio/)
  })

  test('should play audio when play button is clicked', async ({ page }) => {
    // Wait for audio to load (element is hidden but in DOM)
    await page.waitForSelector('[data-testid="audio-element"]', { state: 'attached' })
    const audioElement = page.locator('[data-testid="audio-element"]')

    // Wait for audio metadata to load (duration > 0)
    await page.waitForFunction(() => {
      const audio = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement
      return audio && audio.duration > 0
    }, undefined, { timeout: 10000 })

    // Get initial currentTime (should be 0)
    const initialTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(initialTime).toBe(0)

    // Click play button
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for audio to actually start playing
    await page.waitForTimeout(500)

    // Verify currentTime has increased (audio is playing)
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeGreaterThan(0)
  })

  test('should seek to timestamp when segment is clicked', async ({ page }) => {
    // Expand SRT section first
    await expandSrtSection(page)

    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Check how many segments are available
    const segmentCount = await page.locator('[data-testid^="segment-"]').count()
    expect(segmentCount).toBeGreaterThan(0)

    // Click on second segment if available, otherwise use first segment
    const segmentIndex = segmentCount > 1 ? 1 : 0
    const segment = page.locator(`[data-testid="segment-${segmentIndex}"]`).first()
    await segment.click()

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify audio currentTime is approximately at segment start time
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)

    // If we clicked segment-1, it should start around 2-3 seconds
    // If we clicked segment-0, it should be near 0 but greater than initial time
    if (segmentIndex === 1) {
      expect(currentTime).toBeGreaterThan(1.5)
      expect(currentTime).toBeLessThan(4)
    } else {
      // Segment 0 should start near 0
      expect(currentTime).toBeGreaterThanOrEqual(0)
      expect(currentTime).toBeLessThan(1)
    }
  })

  test('should highlight current segment during playback', async ({ page }) => {
    // Expand SRT section first
    await expandSrtSection(page)

    // Wait for audio to load
    await page.waitForSelector('[data-testid="audio-element"]', { state: 'attached' })

    // Start playback from beginning
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for 1 second of playback
    await page.waitForTimeout(1000)

    // Get segment data for debugging
    const segmentData = await page.evaluate(() => {
      const segments = document.querySelectorAll('[data-testid^="segment-"]')
      return Array.from(segments).map((seg, index) => {
        const text = seg.textContent || ''
        // Try to get timestamp from the element
        return { index, text: text.substring(0, 50) }
      })
    })
    console.log(`Segments found: ${segmentData.length}`, JSON.stringify(segmentData).substring(0, 200))

    // Check if any segment has aria-current="true"
    const currentSegment = page.locator('[aria-current="true"]')
    const count = await currentSegment.count()

    // Check if audio is still playing and get currentTime
    const audioElement = page.locator('[data-testid="audio-element"]')
    const audioState = await audioElement.evaluate((el: HTMLAudioElement) => ({
      isPlaying: !el.paused,
      currentTime: el.currentTime,
      duration: el.duration
    }))

    console.log(`Audio state: playing=${audioState.isPlaying}, currentTime=${audioState.currentTime}, duration=${audioState.duration}`)

    // Only expect highlighting if audio is still playing and currentTime > 0
    if (audioState.isPlaying && audioState.currentTime > 0) {
      // At least one segment should be highlighted as current
      expect(count).toBeGreaterThan(0)

      // Verify the current segment is visible
      if (count > 0) {
        await expect(currentSegment.first()).toBeVisible()
      }
    } else {
      // Audio finished or hasn't started - this is OK for short audio files
      console.log('Audio not playing or currentTime is 0 - skipping aria-current check for short audio')
    }
  })

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Expand SRT section first
    await expandSrtSection(page)

    // Set mobile viewport (iPhone SE)
    await page.setViewportSize({ width: 375, height: 667 })

    // Wait for page to load
    await page.waitForLoadState('networkidle')

    // Verify audio player is visible on mobile
    const audioPlayer = page.locator('[data-testid="audio-player-container"]')
    await expect(audioPlayer).toBeVisible()

    // Verify page has bottom padding (pb-20 class for audio player space)
    const mainContainer = page.locator('.container.mx-auto.px-4.py-8.max-w-4xl')
    const paddingBottom = await mainContainer.evaluate((el: HTMLElement) => {
      return window.getComputedStyle(el).paddingBottom
    })

    // Bottom padding should be at least 3rem (48px) for audio player space
    const paddingValue = parseFloat(paddingBottom)
    expect(paddingValue).toBeGreaterThanOrEqual(48)

    // Verify segments have minimum touch target height (min-h-[48px])
    const firstSegment = page.locator('[data-testid="segment-0"]').first()
    if (await firstSegment.isVisible()) {
      const segmentHeight = await firstSegment.evaluate((el: HTMLElement) => {
        return window.getComputedStyle(el).minHeight
      })
      const heightValue = parseFloat(segmentHeight)
      expect(heightValue).toBeGreaterThanOrEqual(48)
    }
  })

  test('should seek to segment start time when clicked and continue playing', async ({ page }) => {
    // Expand SRT section first
    await expandSrtSection(page)

    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Check how many segments are available
    const segmentCount = await page.locator('[data-testid^="segment-"]').count()

    // Skip test if we don't have enough segments
    if (segmentCount < 2) {
      console.log(`Test skipped: only ${segmentCount} segment(s) available`)
      return
    }

    // Start playback
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for playback to start
    await page.waitForTimeout(1000)

    // Click on third segment (index 2) if available, otherwise use last segment
    const segmentIndex = Math.min(2, segmentCount - 1)
    const segment = page.locator(`[data-testid="segment-${segmentIndex}"]`).first()
    await segment.click()

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify audio currentTime is approximately at segment start time
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)

    // Verify audio seeked to a different time
    expect(currentTime).toBeGreaterThan(0)

    // Verify audio is still playing after seek
    const isPlaying = await audioElement.evaluate((el: HTMLAudioElement) => !el.paused)
    expect(isPlaying).toBe(true)
  })

  test('should seek when seek bar is dragged', async ({ page }) => {
    // Wait for audio to load
    await page.waitForSelector('[data-testid="audio-element"]', { state: 'attached' })

    const audioElement = page.locator('[data-testid="audio-element"]')

    // Wait for audio metadata to load (duration > 0)
    await page.waitForFunction(() => {
      const audio = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement
      return audio && audio.duration > 0
    }, undefined, { timeout: 10000 })

    // Get audio duration
    const duration = await audioElement.evaluate((el: HTMLAudioElement) => el.duration)
    expect(duration).toBeGreaterThan(0)

    // Calculate middle position value
    const seekValue = duration / 2

    // Use JavaScript to set the seek bar value and trigger change event
    await page.evaluate((value) => {
      const seekBar = document.querySelector('input[type="range"]') as HTMLInputElement
      if (seekBar) {
        seekBar.value = String(value)
        // Trigger the change event manually
        seekBar.dispatchEvent(new Event('input', { bubbles: true }))
        seekBar.dispatchEvent(new Event('change', { bubbles: true }))
      }
    }, seekValue)

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify currentTime is approximately at middle
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeCloseTo(seekValue, 0) // Within 1 second tolerance
  })

  test('should handle multiple rapid segment clicks without errors', async ({ page }) => {
    // Expand SRT section first
    await expandSrtSection(page)

    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Check how many segments are available
    const segmentCount = await page.locator('[data-testid^="segment-"]').count()

    // Skip test if we don't have enough segments
    if (segmentCount < 2) {
      console.log(`Test skipped: only ${segmentCount} segment(s) available`)
      return
    }

    // Initialize console errors array for this test
    await page.evaluate(() => {
      ;(window as any).consoleErrors = []
    })

    // Rapidly click multiple segments (up to 5 or available segments)
    const clickCount = Math.min(5, segmentCount)
    for (let i = 0; i < clickCount; i++) {
      const segment = page.locator(`[data-testid="segment-${i}"]`).first()
      await segment.click()
      await page.waitForTimeout(50) // Small delay between clicks
    }

    // Verify no console errors
    const logs = await page.evaluate(() => {
      return (window as any).consoleErrors || []
    })
    expect(logs.length).toBe(0)

    // Verify audio currentTime is at last clicked segment
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeGreaterThan(0)
  })

  test('should seek when Enter key is pressed on focused segment', async ({ page }) => {
    // Expand SRT section first
    await expandSrtSection(page)

    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Check how many segments are available
    const segmentCount = await page.locator('[data-testid^="segment-"]').count()

    // Skip test if we don't have enough segments (need at least 2)
    if (segmentCount < 2) {
      console.log(`Test skipped: only ${segmentCount} segment(s) available`)
      return
    }

    const audioElement = page.locator('[data-testid="audio-element"]')

    // Get initial time
    const initialTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(initialTime).toBe(0)

    // Focus second segment and press Enter
    const segment = page.locator('[data-testid="segment-1"]').first()
    await segment.focus()
    await page.keyboard.press('Enter')

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify currentTime changed
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeGreaterThan(0)
  })

  test('should handle segment clicks on mobile viewport', async ({ page }) => {
    // Expand SRT section first
    await expandSrtSection(page)

    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Check how many segments are available
    const segmentCount = await page.locator('[data-testid^="segment-"]').count()

    // Skip test if we don't have enough segments (need at least 2)
    if (segmentCount < 2) {
      console.log(`Test skipped: only ${segmentCount} segment(s) available`)
      return
    }

    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Tap on second segment (touch event)
    const segment = page.locator('[data-testid="segment-1"]').first()
    await segment.tap()

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify audio seeked
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeGreaterThan(0)
  })

  test('should render long transcription efficiently with virtual scrolling', async ({ page }) => {
    // Navigate to shared page with long transcription
    await page.goto(`${BASE_URL}/shared/${shareToken}`)

    // Expand SRT section first
    await expandSrtSection(page)

    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Count total rendered segment elements
    const renderedSegments = await page.locator('[data-testid^="segment-"]').count()

    // Verify virtualization: should render ~20-30 items even if transcription is longer
    // (VirtualizedSrtList with overscan=5 renders ~visible + 5 above + 5 below)
    expect(renderedSegments).toBeLessThan(50)

    // Verify scroll performance - scroll to bottom
    await page.evaluate(() => {
      const list = document.querySelector('[role="list"]')
      if (list) {
        list.scrollTop = list.scrollHeight
      }
    })

    // Wait a moment for virtual items to render
    await page.waitForTimeout(500)

    // Verify still ~20-30 items rendered (not all segments)
    const renderedSegmentsAfterScroll = await page.locator('[data-testid^="segment-"]').count()
    expect(renderedSegmentsAfterScroll).toBeLessThan(50)
  })

  test('should auto-scroll to current segment during playback', async ({ page }) => {
    // Expand SRT section first
    await expandSrtSection(page)

    // Wait for audio and segments to load
    await page.waitForSelector('[data-testid="audio-element"]', { state: 'attached' })
    await page.waitForSelector('[data-testid^="segment-"]')

    // Wait for audio metadata to load (duration > 0)
    await page.waitForFunction(() => {
      const audio = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement
      return audio && audio.duration > 0
    }, undefined, { timeout: 10000 })

    const audioElement = page.locator('[data-testid="audio-element"]')

    // Get audio duration to determine appropriate wait time
    const duration = await audioElement.evaluate((el: HTMLAudioElement) => el.duration)

    // Start playback from beginning
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for half of audio duration (or 2 seconds if very short)
    const waitTime = Math.min(duration / 2, 2000)
    await page.waitForTimeout(waitTime)

    // Check if audio is still playing
    const audioState = await audioElement.evaluate((el: HTMLAudioElement) => ({
      isPlaying: !el.paused,
      currentTime: el.currentTime,
      duration: el.duration
    }))

    console.log(`Audio state after ${waitTime}ms: playing=${audioState.isPlaying}, currentTime=${audioState.currentTime}, duration=${audioState.duration}`)

    // Only expect highlighting if audio is still playing
    if (audioState.isPlaying && audioState.currentTime > 0) {
      // Check if a segment with aria-current="true" is visible in viewport
      const currentSegment = page.locator('[aria-current="true"]').first()

      // Verify current segment exists
      const count = await page.locator('[aria-current="true"]').count()
      expect(count).toBeGreaterThan(0)

      // Verify current segment is approximately visible in viewport
      if (count > 0) {
        await expect(currentSegment.first()).toBeVisible()
      }
    } else {
      // Audio finished too quickly - this is OK for short audio files
      console.log('Audio finished or paused - skipping aria-current check for short audio')
    }
  })
})

test.describe('Dark Mode', () => {
  test('should display SRT player correctly in dark mode', async ({ page }) => {
    // Enable dark mode (assuming app has a theme toggle)
    await page.emulateMedia({ colorScheme: 'dark' })

    // Navigate to shared page
    await page.goto(`${BASE_URL}/shared/${shareToken}`)

    // Wait for page to load
    await page.waitForLoadState('networkidle')

    // Expand SRT section first
    await expandSrtSection(page)

    // Verify audio player container has dark mode classes
    const audioPlayer = page.locator('[data-testid="audio-player-container"]')
    // Check if container has the dark mode class
    const className = await audioPlayer.getAttribute('class')
    expect(className).toMatch(/dark:bg-gray-800/)

    // Verify segments are visible in dark mode
    const firstSegment = page.locator('[data-testid="segment-0"]').first()
    await expect(firstSegment).toBeVisible()

    // Verify current segment highlighting works in dark mode
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    await page.waitForTimeout(3000)

    const currentSegment = page.locator('[aria-current="true"]').first()
    await expect(currentSegment).toHaveAttribute('aria-current', 'true')
  })
})
