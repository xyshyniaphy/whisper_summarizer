import { describe, it, expect, vi } from "vitest"

// Try mocking the exact path the component uses
const { mockGetTranscriptions } = vi.hoisted(() => ({
  mockGetTranscriptions: vi.fn()
}))

vi.mock("../../src/services/api", () => ({
  api: {
    getTranscriptions: mockGetTranscriptions
  }
}))

vi.mock("../../src/services/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null }, error: null }))
    }
  }
}))

describe("Module ID test", () => {
  it("should import api module", async () => {
    const { api } = await import("../../src/services/api")
    console.log("API module:", api)
    console.log("Mock calls:", mockGetTranscriptions.mock.calls)
  })
})
