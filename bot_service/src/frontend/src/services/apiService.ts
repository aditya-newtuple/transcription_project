import axios from 'axios';
import { CreateJobResponse, JobWithFiles, FileWithTranscripts, FileInfo } from '../types';

// Get API base URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://0.0.0.0:8081/';

// Simple API service with just the requested job creation endpoint
export const createJob = async (currentUserId: number, files: File[]): Promise<CreateJobResponse> => {
  const formData = new FormData();
  
  // Add files to form data
  files.forEach((file, index) => {
    formData.append('files', file);
  });

  const response = await axios.post<CreateJobResponse>(
    `${API_BASE_URL}v1/api/jobs`,
    formData,
    { 
      params: { current_user_id: currentUserId },
      headers: {
        'Content-Type': 'multipart/form-data',
      }
    }
  );
  return response.data;
};

// Get job details with files
export const getJob = async (jobId: number): Promise<JobWithFiles> => {
  const response = await axios.get<JobWithFiles>(`${API_BASE_URL}v1/api/jobs/${jobId}`);
  return response.data;
};

// Get file details with transcripts
export const getFile = async (fileId: number): Promise<FileWithTranscripts> => {
  const response = await axios.get<FileWithTranscripts>(`${API_BASE_URL}v1/api/files/${fileId}`);
  return response.data;
};

// List all files
export const listFiles = async (pageSize: number = 10): Promise<FileInfo[]> => {
  const response = await axios.get<FileInfo[]>(`${API_BASE_URL}v1/api/files`, {
    params: { page_size: pageSize }
  });
  return response.data;
};

export const getDiskSpace = async (): Promise<{
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percentage: number;
  status: string;
}> => {
  const response = await axios.get(`${API_BASE_URL}v1/api/disk-space`);
  return response.data;
};

// Delete a file by ID
export const deleteFile = async (fileId: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}v1/api/files/${fileId}`);
};
