import { describe, it, expect, vi, beforeEach } from "vitest"

const mockGetTranscriptions = vi.fn()

vi.mock("../src/services/api", () => ({
  api: {
    getTranscriptions: mockGetTranscriptions
  }
}))

const mockTranscriptions = [
  {
    id: "1",
    file_name: "test-audio.mp3",
    created_at: "2024-01-01T00:00:00Z"
  }
]

describe("Debug Mock", () => {
  beforeEach(() => {
    mockGetTranscriptions.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
      data: mockTranscriptions
    })
  })

  it("test mock is called", async () => {
    expect(mockGetTranscriptions).toBeDefined()
    const result = await mockGetTranscriptions()
    expect(result.data).toHaveLength(1)
    expect(result.data[0].file_name).toBe("test-audio.mp3")
  })
})
