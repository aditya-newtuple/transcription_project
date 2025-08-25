import axios from 'axios';
import { CreateJobResponse, JobWithFiles, FileWithTranscripts, FileInfo } from '../types';

// Simple API service with just the requested job creation endpoint
export const createJob = async (currentUserId: number, files: File[]): Promise<CreateJobResponse> => {
  const formData = new FormData();
  
  // Add files to form data
  files.forEach((file, index) => {
    formData.append('files', file);
  });

  const response = await axios.post<CreateJobResponse>(
    'http://0.0.0.0:8081/v1/api/jobs',
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
  const response = await axios.get<JobWithFiles>(`http://0.0.0.0:8081/v1/api/jobs/${jobId}`);
  return response.data;
};

// Get file details with transcripts
export const getFile = async (fileId: number): Promise<FileWithTranscripts> => {
  const response = await axios.get<FileWithTranscripts>(`http://0.0.0.0:8081/v1/api/files/${fileId}`);
  return response.data;
};

// List all files
export const listFiles = async (pageSize: number = 10): Promise<FileInfo[]> => {
  const response = await axios.get<FileInfo[]>(`http://0.0.0.0:8081/v1/api/files`, {
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
  const response = await axios.get(`http://0.0.0.0:8081/v1/api/disk-space`);
  return response.data;
};
