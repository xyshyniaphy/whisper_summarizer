import axios from 'axios';
import { supabase } from './supabase';
import { Transcription, PaginatedResponse } from '../types';

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

  getTranscriptions: async (page: number = 1, page_size?: number, channel_id?: string): Promise<PaginatedResponse<Transcription>> => {
    const params: Record<string, number | string> = { page };
    if (page_size !== undefined) {
      params.page_size = page_size;
    }
    if (channel_id !== undefined) {
      params.channel_id = channel_id;
    }
    const response = await apiClient.get<PaginatedResponse<Transcription>>('/transcriptions', { params });
    return response.data;
  },

  getTranscription: async (id: string): Promise<Transcription> => {
    const response = await apiClient.get<Transcription>(`/transcriptions/${id}`);
    return response.data;
  },

  deleteTranscription: async (id: string): Promise<void> => {
    await apiClient.delete(`/transcriptions/${id}`);
  },

  deleteAllTranscriptions: async (): Promise<{ deleted_count: number; message: string }> => {
    const response = await apiClient.delete<{ deleted_count: number; message: string }>('/transcriptions/all');
    return response.data;
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
  },

  downloadSummaryDocx: async (transcriptionId: string): Promise<Blob> => {
    const response = await apiClient.get(`/transcriptions/${transcriptionId}/download-docx`, {
      responseType: 'blob'
    });
    return response.data;
  },

  downloadNotebookLMGuideline: async (transcriptionId: string): Promise<Blob> => {
    const response = await apiClient.get(`/transcriptions/${transcriptionId}/download-notebooklm`, {
      responseType: 'blob'
    });
    return response.data;
  },

  // Chat endpoints
  getChatHistory: async (transcriptionId: string): Promise<{ messages: Array<{
    id: string;
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
  }> }> => {
    console.log('[API] Fetching chat history for:', transcriptionId);
    const response = await apiClient.get(`/transcriptions/${transcriptionId}/chat`);
    console.log('[API] Chat history response:', response.status, response.data);
    return response.data;
  },

  sendChatMessage: async (transcriptionId: string, content: string): Promise<{
    id: string;
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
  }> => {
    console.log('[API] Sending chat message:', { transcriptionId, content });
    const response = await apiClient.post(`/transcriptions/${transcriptionId}/chat`, { content });
    console.log('[API] Chat message response:', response.status, response.data);
    return response.data;
  },

  sendChatMessageStream: async (
    transcriptionId: string,
    content: string,
    onChunk: (chunk: string) => void,
    onError?: (error: string) => void,
    onComplete?: () => void
  ): Promise<void> => {
    console.log('[API] Starting stream chat:', { transcriptionId, content });

    // Get current session from Supabase
    const { data: { session } } = await supabase.auth.getSession();

    const response = await fetch(`${API_URL}/transcriptions/${transcriptionId}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session?.access_token || ''}`,
      },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      throw new Error(`Stream error: ${response.status} ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('[API] Stream complete');
          onComplete?.();
          break;
        }

        // Decode the chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const data = JSON.parse(jsonStr);

              if (data.error) {
                console.error('[API] Stream error:', data.error);
                onError?.(data.error);
                return;
              }

              if (data.content && !data.done) {
                onChunk(data.content);
              }

              if (data.done) {
                console.log('[API] Stream done signal received');
                onComplete?.();
                return;
              }
            } catch (e) {
              console.error('[API] Failed to parse SSE data:', jsonStr, e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  // Share endpoints
  createShareLink: async (transcriptionId: string): Promise<{
    id: string;
    transcription_id: string;
    share_token: string;
    share_url: string;
    created_at: string;
    access_count: number;
  }> => {
    const response = await apiClient.post(`/transcriptions/${transcriptionId}/share`);
    return response.data;
  },

  getSharedTranscription: async (shareToken: string): Promise<{
    id: string;
    file_name: string;
    text: string;
    summary: string | null;
    language: string | null;
    duration_seconds: number | null;
    created_at: string;
  }> => {
    const response = await axios.get(`${API_URL}/shared/${shareToken}`);
    return response.data;
  },

  // Channel endpoints
  getTranscriptionChannels: async (transcriptionId: string): Promise<Array<{
    id: string;
    name: string;
    description?: string;
  }>> => {
    const response = await apiClient.get(`/transcriptions/${transcriptionId}/channels`);
    return response.data;
  },

  assignTranscriptionToChannels: async (transcriptionId: string, channelIds: string[]): Promise<{
    message: string;
    channel_ids: string[];
  }> => {
    const response = await apiClient.post(`/transcriptions/${transcriptionId}/channels`, { channel_ids });
    return response.data;
  },
};

// Admin API endpoints
export const adminApi = {
  // User management
  listUsers: async (): Promise<Array<{
    id: string;
    email: string;
    is_active: boolean;
    is_admin: boolean;
    activated_at: string | null;
    created_at: string;
  }>> => {
    const response = await apiClient.get('/admin/users');
    return response.data;
  },

  activateUser: async (userId: string): Promise<any> => {
    const response = await apiClient.put(`/admin/users/${userId}/activate`);
    return response.data;
  },

  toggleUserAdmin: async (userId: string, is_admin: boolean): Promise<any> => {
    const response = await apiClient.put(`/admin/users/${userId}/admin`, { is_admin });
    return response.data;
  },

  deleteUser: async (userId: string): Promise<any> => {
    const response = await apiClient.delete(`/admin/users/${userId}`);
    return response.data;
  },

  // Channel management
  listChannels: async (): Promise<Array<{
    id: string;
    name: string;
    description?: string;
    created_by?: string;
    created_at: string;
    updated_at: string;
    member_count?: number;
  }>> => {
    const response = await apiClient.get('/admin/channels');
    return response.data;
  },

  createChannel: async (data: { name: string; description?: string }): Promise<any> => {
    const response = await apiClient.post('/admin/channels', data);
    return response.data;
  },

  updateChannel: async (channelId: string, data: { name?: string; description?: string }): Promise<any> => {
    const response = await apiClient.put(`/admin/channels/${channelId}`, data);
    return response.data;
  },

  deleteChannel: async (channelId: string): Promise<any> => {
    const response = await apiClient.delete(`/admin/channels/${channelId}`);
    return response.data;
  },

  assignUserToChannel: async (channelId: string, userId: string): Promise<any> => {
    const response = await apiClient.post(`/admin/channels/${channelId}/members`, { user_id: userId });
    return response.data;
  },

  removeUserFromChannel: async (channelId: string, userId: string): Promise<any> => {
    const response = await apiClient.delete(`/admin/channels/${channelId}/members/${userId}`);
    return response.data;
  },

  getChannelDetail: async (channelId: string): Promise<any> => {
    const response = await apiClient.get(`/admin/channels/${channelId}`);
    return response.data;
  },

  // Audio management
  listAllAudio: async (): Promise<any> => {
    const response = await apiClient.get('/admin/audio');
    return response.data;
  },

  assignAudioToChannels: async (audioId: string, channelIds: string[]): Promise<any> => {
    const response = await apiClient.post(`/admin/audio/${audioId}/channels`, { channel_ids: channelIds });
    return response.data;
  },

  getAudioChannels: async (audioId: string): Promise<any[]> => {
    const response = await apiClient.get(`/admin/audio/${audioId}/channels`);
    return response.data;
  },
};
