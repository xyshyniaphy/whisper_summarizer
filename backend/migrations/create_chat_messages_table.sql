-- Create chat_messages table for AI Q&A about transcriptions
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    role VARCHAR NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on transcription_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_chat_messages_transcription_id ON chat_messages(transcription_id);

-- Create index on user_id for user's chat history
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);

-- Create index on created_at for sorting by time
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
