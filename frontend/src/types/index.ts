export interface Transcription {
  id: string;
  file_name: string;
  file_path?: string;
  original_text?: string;
  status: 'processing' | 'completed' | 'failed';
  language?: string;
  duration_seconds?: number;
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
