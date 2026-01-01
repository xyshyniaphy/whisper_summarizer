export interface Transcription {
  id: string;
  file_name: string;
  file_path?: string;
  // text is a @property that reads from local filesystem, not a database column
  text: string;
  stage: 'uploading' | 'transcribing' | 'summarizing' | 'completed' | 'failed';
  language?: string;
  duration_seconds?: number;
  error_message?: string;
  retry_count?: number;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  time_remaining?: number;  // Seconds remaining before auto-delete (negative if expired)
  summaries?: Summary[];
  pptx_status?: 'not-started' | 'generating' | 'ready' | 'error';
  pptx_error_message?: string;
}

export interface Summary {
  id: string;
  transcription_id: string;
  summary_text: string;
  model_name?: string;
  created_at: string;
}

export interface UploadResponse extends Transcription {}
