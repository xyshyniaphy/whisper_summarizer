/**
 * Check if E2E test mode is enabled.
 *
 * Requires BOTH conditions for security:
 * 1. localStorage flag 'e2e-test-mode' === 'true'
 * 2. Accessing via localhost or Docker internal hostname (not production domain)
 *
 * This ensures production users (accessing via w.198066.xyz) cannot bypass
 * authentication even if they set the localStorage flag.
 */
export function isE2ETestMode(): boolean {
  if (typeof window === 'undefined') {
    return false
  }

  // Check localStorage flag
  const flag = localStorage.getItem('e2e-test-mode')
  if (flag !== 'true') {
    return false
  }

  // Check hostname is localhost or Docker internal (safety check for production)
  const hostname = window.location.hostname
  const isLocalhost = hostname === 'localhost' ||
                      hostname === '127.0.0.1' ||
                      hostname === '::1' ||
                      // Docker internal hostnames for E2E testing
                      hostname === 'whisper_frontend_dev' ||
                      hostname === 'frontend-test'

  return isLocalhost
}

/**
 * Set E2E test mode flag in localStorage.
 * Only works when accessing via localhost for security.
 */
export function setE2ETestMode(enabled: boolean): void {
  if (typeof window === 'undefined') {
    return
  }

  // Security check: only allow setting on localhost
  const hostname = window.location.hostname
  const isLocalhost = hostname === 'localhost' ||
                      hostname === '127.0.0.1' ||
                      hostname === '::1'

  if (!isLocalhost) {
    console.warn('[E2E] Cannot enable test mode on non-localhost hostname:', hostname)
    return
  }

  if (enabled) {
    localStorage.setItem('e2e-test-mode', 'true')
  } else {
    localStorage.removeItem('e2e-test-mode')
  }
}
