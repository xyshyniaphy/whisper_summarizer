import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { BrowserRouter } from "react-router-dom"
import { Provider } from "jotai"

const mockGetTranscriptions = vi.fn()
const mockDeleteTranscription = vi.fn()

vi.mock("../src/services/api", () => ({
  api: {
    getTranscriptions: mockGetTranscriptions,
    deleteTranscription: mockDeleteTranscription
  }
}))

const { TranscriptionList } = await import("../src/pages/TranscriptionList")

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <Provider>{children}</Provider>
  </BrowserRouter>
)

const mockTranscriptions = [
  {
    id: "1",
    user_id: "user-1",
    file_name: "test-audio.mp3",
    original_text: "Test transcription text",
    language: "zh",
    duration_seconds: 120.5,
    stage: "completed",
    error_message: null,
    retry_count: 0,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:05:00Z",
    summaries: []
  }
]

describe("Debug TranscriptionList", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetTranscriptions.mockResolvedValue({
      total: mockTranscriptions.length,
      page: 1,
      page_size: 10,
      total_pages: 1,
      data: mockTranscriptions
    })
    mockDeleteTranscription.mockResolvedValue(undefined)
  })

  it("should render transcriptions", async () => {
    render(<TranscriptionList />, { wrapper })

    await waitFor(() => {
      console.log("Mock calls:", mockGetTranscriptions.mock.calls)
      console.log("Mock results:", mockGetTranscriptions.mock.results)
    }, { timeout: 5000 })
  })
})
