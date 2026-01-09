-- Migration: Create gemini_request_logs table
-- Description: Stores detailed information about Gemini API requests for debugging

CREATE TABLE IF NOT EXISTS gemini_request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    file_name VARCHAR(500),
    model_name VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    input_text TEXT NOT NULL,
    input_text_length INTEGER NOT NULL,
    output_text TEXT,
    output_text_length INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    response_time_ms FLOAT,
    temperature FLOAT,
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_gemini_request_logs_transcription_id ON gemini_request_logs(transcription_id);
CREATE INDEX IF NOT EXISTS idx_gemini_request_logs_status ON gemini_request_logs(status);
CREATE INDEX IF NOT EXISTS idx_gemini_request_logs_created_at ON gemini_request_logs(created_at DESC);

-- Add comment for documentation
COMMENT ON TABLE gemini_request_logs IS 'Detailed logs of Gemini API requests for debugging and analysis';
COMMENT ON COLUMN gemini_request_logs.transcription_id IS 'Reference to the transcription being summarized';
COMMENT ON COLUMN gemini_request_logs.file_name IS 'Original audio file name';
COMMENT ON COLUMN gemini_request_logs.model_name IS 'Gemini model used (e.g., gemini-2.0-flash-exp)';
COMMENT ON COLUMN gemini_request_logs.prompt IS 'System prompt used for generation';
COMMENT ON COLUMN gemini_request_logs.input_text IS 'Input transcription text (truncated)';
COMMENT ON COLUMN gemini_request_logs.input_tokens IS 'Input token count from API response';
COMMENT ON COLUMN gemini_request_logs.output_tokens IS 'Output token count from API response';
COMMENT ON COLUMN gemini_request_logs.total_tokens IS 'Total token count from API response';
COMMENT ON COLUMN gemini_request_logs.response_time_ms IS 'API response time in milliseconds';
COMMENT ON COLUMN gemini_request_logs.temperature IS 'Temperature setting used';
COMMENT ON COLUMN gemini_request_logs.status IS 'Request status: success, error, timeout';
COMMENT ON COLUMN gemini_request_logs.error_message IS 'Error details if request failed';
