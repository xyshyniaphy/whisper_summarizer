import axios from 'axios';
import { supabase } from './supabase';
import { Transcription, Summary } from '../types';

// API URL - relative path works with both Vite dev proxy and Nginx production proxy
const API_URL = '/api';

// Create axios instance with interceptors for auth
const apiClient = axios.create({
  baseURL: API_URL,
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  async (config) => {
    // Get current session from Supabase
    const { data: { session } } = await supabase.auth.getSession();

    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh the session
        const { data: { session } } = await supabase.auth.refreshSession();

        if (session?.access_token) {
          // Retry the original request with new token
          originalRequest.headers.Authorization = `Bearer ${session.access_token}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // If refresh fails, sign out
        await supabase.auth.signOut();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export const api = {
  uploadAudio: async (file: File): Promise<Transcription> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<Transcription>('/audio/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getTranscriptions: async (): Promise<Transcription[]> => {
    const response = await apiClient.get<Transcription[]>('/transcriptions');
    return response.data;
  },

  getTranscription: async (id: string): Promise<Transcription> => {
    const response = await apiClient.get<Transcription>(`/transcriptions/${id}`);
    return response.data;
  },

  deleteTranscription: async (id: string): Promise<void> => {
    await apiClient.delete(`/transcriptions/${id}`);
  },

  getDownloadUrl: (transcriptionId: string, format: 'txt' | 'srt'): string => {
    return `${API_URL}/transcriptions/${transcriptionId}/download?format=${format}`;
  },

  downloadFile: async (transcriptionId: string, format: 'txt' | 'srt'): Promise<Blob> => {
    // Use relative path since apiClient already has baseURL = '/api'
    const response = await apiClient.get(`/transcriptions/${transcriptionId}/download?format=${format}`, {
      responseType: 'blob'
    });
    return response.data;
  }
};
