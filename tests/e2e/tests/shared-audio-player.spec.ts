/**
 * Shared Audio Player E2E Tests
 *
 * Tests for audio player with SRT navigation on shared transcription pages.
 * Verifies audio playback, segment seeking, and current segment highlighting.
 */

import { test, expect } from '@playwright/test'
import { getOrCreateSharedTranscriptionWithShare } from '../helpers/test-data'

const BASE_URL = process.env.BASE_URL || 'http://localhost:8130'

// Declare shareToken at module level so both test.describe blocks can access it
let shareToken: string

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
    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Click on second segment (index 1, should be around 2 seconds)
    const segment = page.locator('[data-testid="segment-1"]').first()
    await segment.click()

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify audio currentTime is approximately at segment start time
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)

    // Segment 1 should start around 2-3 seconds (allowing some tolerance)
    expect(currentTime).toBeGreaterThan(1.5)
    expect(currentTime).toBeLessThan(4)
  })

  test('should highlight current segment during playback', async ({ page }) => {
    // Wait for audio to load
    await page.waitForSelector('[data-testid="audio-element"]', { state: 'attached' })

    // Start playback from beginning
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for 3 seconds of playback
    await page.waitForTimeout(3000)

    // Check if any segment has aria-current="true"
    const currentSegment = page.locator('[aria-current="true"]')
    const count = await currentSegment.count()

    // At least one segment should be highlighted as current
    expect(count).toBeGreaterThan(0)

    // Verify the current segment is visible
    if (count > 0) {
      await expect(currentSegment.first()).toBeVisible()
    }
  })

  test('should be responsive on mobile viewport', async ({ page }) => {
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
    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Start playback
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for playback to start
    await page.waitForTimeout(1000)

    // Click on third segment (index 2)
    const segment = page.locator('[data-testid="segment-2"]').first()
    await segment.click()

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify audio currentTime is approximately at segment start time
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)

    // Segment 2 should be around 10+ seconds
    expect(currentTime).toBeGreaterThan(9)

    // Verify audio is still playing after seek
    const isPlaying = await audioElement.evaluate((el: HTMLAudioElement) => !el.paused)
    expect(isPlaying).toBe(true)
  })

  test('should seek when seek bar is dragged', async ({ page }) => {
    // Wait for audio to load
    await page.waitForSelector('[data-testid="audio-element"]', { state: 'attached' })

    const audioElement = page.locator('[data-testid="audio-element"]')
    const seekBar = page.locator('input[type="range"]')

    // Get initial max value (duration)
    const max = await seekBar.getAttribute('max')

    // Click at 50% of seek bar
    await seekBar.click({
      position: { x: 0.5, y: 0 } // Click at middle horizontally
    })

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify currentTime is approximately at middle
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)

    if (max) {
      const expectedTime = parseFloat(max) * 0.5
      expect(currentTime).toBeCloseTo(expectedTime, 0) // Within 1 second tolerance
    }
  })

  test('should handle multiple rapid segment clicks without errors', async ({ page }) => {
    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Initialize console errors array for this test
    await page.evaluate(() => {
      ;(window as any).consoleErrors = []
    })

    // Rapidly click multiple segments
    for (let i = 0; i < 5; i++) {
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
    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

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
    expect(currentTime).toBeGreaterThan(1)
  })

  test('should handle segment clicks on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Wait for segments to load
    await page.waitForSelector('[data-testid^="segment-"]')

    // Tap on second segment (touch event)
    const segment = page.locator('[data-testid="segment-1"]').first()
    await segment.tap()

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify audio seeked
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeGreaterThan(1)
  })

  test('should render long transcription efficiently with virtual scrolling', async ({ page }) => {
    // Navigate to shared page with long transcription
    await page.goto(`${BASE_URL}/shared/${shareToken}`)

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
    // Wait for audio and segments to load
    await page.waitForSelector('[data-testid="audio-element"]', { state: 'attached' })
    await page.waitForSelector('[data-testid^="segment-"]')

    // Start playback from beginning
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for 5 seconds of playback
    await page.waitForTimeout(5000)

    // Check if a segment with aria-current="true" is visible in viewport
    const currentSegment = page.locator('[aria-current="true"]').first()

    // Verify current segment exists
    await expect(currentSegment).toHaveAttribute('aria-current', 'true')

    // Verify current segment is approximately visible in viewport
    const isVisible = await currentSegment.isVisible()
    expect(isVisible).toBe(true)
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
