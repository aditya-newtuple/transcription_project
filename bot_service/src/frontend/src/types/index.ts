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