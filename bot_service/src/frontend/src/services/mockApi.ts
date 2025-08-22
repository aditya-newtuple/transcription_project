import { User, Transcript, DashboardStats } from '../types';

// Mock data storage
const mockUsers: User[] = [
  {
    id: '1',
    name: 'Admin User',
    email: 'admin@example.com',
    role: 'admin',
    createdAt: '2024-01-01T00:00:00Z'
  },
  {
    id: '2',
    name: 'John Doe',
    email: 'john@example.com',
    role: 'user',
    createdAt: '2024-01-02T00:00:00Z'
  }
];

const mockTranscripts: Transcript[] = [
  {
    id: '1',
    userId: '2',
    fileName: 'meeting-recording.mp3',
    fileUrl: 'https://www.soundjay.com/misc/sounds/bell-ringing-05.wav',
    fileType: 'audio',
    status: 'completed',
    createdAt: '2024-01-10T10:00:00Z',
    completedAt: '2024-01-10T10:05:00Z',
    duration: 120,
    srtUrl: '/mock-subtitle.srt',
    transcriptText: 'Hello, this is a test transcript. Welcome to our meeting.',
    accepted: false
  },
  {
    id: '2',
    userId: '2',
    fileName: 'interview.mp4',
    fileUrl: 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4',
    fileType: 'video',
    status: 'processing',
    createdAt: '2024-01-11T14:00:00Z',
    duration: 180,
    progress: 75,
    accepted: false
  },
  {
    id: '3',
    userId: '2',
    fileName: 'meeting-recording1.mp3',
    fileUrl: 'https://www.soundjay.com/misc/sounds/bell-ringing-05.wav',
    fileType: 'audio',
    status: 'completed',
    createdAt: '2024-01-10T10:00:00Z',
    completedAt: '2024-01-10T10:05:00Z',
    duration: 120,
    srtUrl: '/mock-subtitle.srt',
    transcriptText: 'Hello, this is a test transcript. Welcome to our meeting.',
    accepted: true
  }
];

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const mockAuthService = {
  async login(email: string, password: string) {
    await delay(1000);
    const user = mockUsers.find(u => u.email === email);
    if (user && password === 'password') {
      return { user, token: 'mock-jwt-token' };
    }
    throw new Error('Invalid credentials');
  },

  async register(name: string, email: string, password: string) {
    await delay(1000);
    const existingUser = mockUsers.find(u => u.email === email);
    if (existingUser) {
      throw new Error('User already exists');
    }
    
    const newUser: User = {
      id: Date.now().toString(),
      name,
      email,
      role: 'user',
      createdAt: new Date().toISOString()
    };
    
    mockUsers.push(newUser);
    return { user: newUser, token: 'mock-jwt-token' };
  }
};

export const mockApiService = {
  async getDashboardStats(userId: string, role: string): Promise<DashboardStats> {
    await delay(500);
    const userTranscripts = mockTranscripts.filter(t => t.userId === userId);
    
    return {
      totalTranscripts: role === 'admin' ? mockTranscripts.length : userTranscripts.length,
      pendingJobs: role === 'admin' 
        ? mockTranscripts.filter(t => t.status === 'pending' || t.status === 'processing').length
        : userTranscripts.filter(t => t.status === 'pending' || t.status === 'processing').length,
      completedJobs: role === 'admin'
        ? mockTranscripts.filter(t => t.status === 'completed').length
        : userTranscripts.filter(t => t.status === 'completed').length,
      totalUsers: role === 'admin' ? mockUsers.length : undefined
    };
  },

  async getTranscripts(userId: string, role: string): Promise<Transcript[]> {
    await delay(500);
    return role === 'admin' ? mockTranscripts : mockTranscripts.filter(t => t.userId === userId);
  },

  async uploadFile(file: File, userId: string): Promise<Transcript> {
    await delay(2000);
    
    const newTranscript: Transcript = {
      id: Date.now().toString(),
      userId,
      fileName: file.name,
      fileUrl: URL.createObjectURL(file),
      fileType: file.type.startsWith('video/') ? 'video' : 'audio',
      status: 'processing',
      createdAt: new Date().toISOString(),
      duration: 0,
      progress: 0,
      accepted: false
    };

    mockTranscripts.push(newTranscript);
    
    // Simulate processing
    setTimeout(() => {
      const transcript = mockTranscripts.find(t => t.id === newTranscript.id);
      if (transcript) {
        transcript.status = 'completed';
        transcript.completedAt = new Date().toISOString();
        transcript.duration = Math.floor(Math.random() * 300) + 60;
        transcript.transcriptText = 'This is a mock transcript generated for the uploaded file.';
        transcript.srtUrl = '/mock-subtitle.srt';
      }
    }, 10000);

    return newTranscript;
  },

  async getUsers(): Promise<User[]> {
    await delay(500);
    return [...mockUsers];
  },

  async updateUserRole(userId: string, role: 'admin' | 'user'): Promise<void> {
    await delay(500);
    const user = mockUsers.find(u => u.id === userId);
    if (user) {
      user.role = role;
    }
  },

  async deleteUser(userId: string): Promise<void> {
    await delay(500);
    const index = mockUsers.findIndex(u => u.id === userId);
    if (index > -1) {
      mockUsers.splice(index, 1);
    }
  },

  async updateProfile(userId: string, updates: Partial<User>): Promise<User> {
    await delay(500);
    const user = mockUsers.find(u => u.id === userId);
    if (user) {
      Object.assign(user, updates);
      return user;
    }
    throw new Error('User not found');
  },

  async acceptTranscript(transcriptId: string): Promise<void> {
    await delay(500);
    const transcript = mockTranscripts.find(t => t.id === transcriptId);
    if (transcript) {
      transcript.accepted = true;
    } else {
      throw new Error('Transcript not found');
    }
  }
};