import axios from 'axios';
import { Transcription } from '../types';

const API_URL = 'http://localhost:8000/api';

export const api = {
  uploadAudio: async (file: File): Promise<Transcription> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await axios.post<Transcription>(`${API_URL}/audio/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getTranscriptions: async (): Promise<Transcription[]> => {
    const response = await axios.get<Transcription[]>(`${API_URL}/transcriptions`);
    return response.data;
  },

  getTranscription: async (id: string): Promise<Transcription> => {
    const response = await axios.get<Transcription>(`${API_URL}/transcriptions/${id}`);
    return response.data;
  },

  deleteTranscription: async (id: string): Promise<void> => {
    await axios.delete(`${API_URL}/transcriptions/${id}`);
  }
};
