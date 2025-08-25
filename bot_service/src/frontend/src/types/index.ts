export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
  createdAt: string;
  avatar?: string;
}

export interface Transcript {
  id: string;
  userId: string;
  fileName: string;
  fileUrl: string;
  fileType: 'audio' | 'video';
  status: 'pending' | 'processing' | 'completed' | 'error';
  createdAt: string;
  completedAt?: string;
  duration?: number;
  srtUrl?: string;
  transcriptText?: string;
  progress?: number;
  accepted?: boolean;
}

export interface Job {
  id: number;
  created_by: number;
  status: 'created' | 'processing' | 'completed' | 'failed';
  total_count: number;
  created_at: string;
  started_at: string;
  finished_at: string;
  message: string;
}

export interface CreateJobResponse {
  id: number;
  created_by: number;
  status: 'created' | 'processing' | 'completed' | 'failed';
  total_count: number;
  created_at: string;
  started_at: string;
  finished_at: string;
  message: string;
}

export interface FileInfo {
  id: number;
  job_id: number;
  created_by: number;
  source_name: string;
  path: string;
  mime_type: string;
  bytes: number;
  deleted_at: string | null;
  status: 'queued' | 'processing' | 'running' | 'succeeded' | 'failed';
  queued_at: string;
  started_at: string;
  finished_at: string | null;
  message: string | null;
}

export interface TranscriptInfo {
  id: number;
  file_id: number;
  version: number;
  format: 'txt' | 'srt';
  content: string;
  created_at: string;
  created_by: number;
  approved_at: string | null;
  approved_by: number | null;
  is_approved: boolean;
}

export interface JobWithFiles {
  id: number;
  created_by: number;
  status: 'created' | 'processing' | 'completed' | 'failed';
  total_count: number;
  created_at: string;
  started_at: string;
  finished_at: string;
  message: string | null;
  files: FileInfo[];
}

export interface FileWithTranscripts {
  id: number;
  job_id: number;
  created_by: number;
  source_name: string;
  path: string;
  mime_type: string;
  bytes: number;
  deleted_at: string | null;
  status: 'queued' | 'processing' | 'succeeded' | 'failed';
  queued_at: string;
  started_at: string;
  finished_at: string;
  message: string | null;
  transcripts: TranscriptInfo[];
}

export interface DashboardStats {
  totalTranscripts: number;
  pendingJobs: number;
  completedJobs: number;
  totalUsers?: number;
}

export interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}