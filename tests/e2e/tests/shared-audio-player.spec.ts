/**
 * Shared Audio Player E2E Tests
 *
 * Tests for audio player with SRT navigation on shared transcription pages.
 * Verifies audio playback, segment seeking, and current segment highlighting.
 */

import { test, expect } from '@playwright/test'

const SHARE_TOKEN = process.env.TEST_SHARE_TOKEN || 'test-share-token'
const BASE_URL = process.env.BASE_URL || 'http://localhost:8130'

test.describe('Shared Audio Player', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to shared transcription page
    await page.goto(`${BASE_URL}/shared/${SHARE_TOKEN}`)
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
    // Wait for audio to load
    await page.waitForSelector('[data-testid="audio-element"]')
    const audioElement = page.locator('[data-testid="audio-element"]')

    // Get initial currentTime (should be 0)
    const initialTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(initialTime).toBe(0)

    // Click play button
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait a moment for playback to start
    await page.waitForTimeout(1000)

    // Verify currentTime has increased
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeGreaterThan(0)
  })

  test('should seek to timestamp when segment is clicked', async ({ page }) => {
    // Wait for segments to load
    await page.waitForSelector('[data-segment-index]')

    // Click on second segment (index 1, should be around 2 seconds)
    const segment = page.locator('[data-segment-index="1"]').first()
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
    await page.waitForSelector('[data-testid="audio-element"]')

    // Start playback from beginning
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for 3 seconds of playback
    await page.waitForTimeout(3000)

    // Check if any segment has data-current="true"
    const currentSegment = page.locator('[data-current="true"]')
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
    const firstSegment = page.locator('[data-segment-index="0"]').first()
    if (await firstSegment.isVisible()) {
      const segmentHeight = await firstSegment.evaluate((el: HTMLElement) => {
        return window.getComputedStyle(el).minHeight
      })
      const heightValue = parseFloat(segmentHeight)
      expect(heightValue).toBeGreaterThanOrEqual(48)
    }
  })
})
