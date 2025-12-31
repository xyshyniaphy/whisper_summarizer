export interface Transcription {
  id: string;
  file_name: string;
  file_path?: string;
  original_text?: string;
  status: 'processing' | 'completed' | 'failed';  // Legacy, use stage instead
  stage: 'uploading' | 'transcribing' | 'summarizing' | 'completed' | 'failed';
  language?: string;
  duration_seconds?: number;
  error_message?: string;
  retry_count?: number;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  summaries?: Summary[];
}

export interface Summary {
  id: string;
  transcription_id: string;
  summary_text: string;
  model_name?: string;
  created_at: string;
}

export interface UploadResponse extends Transcription {}
