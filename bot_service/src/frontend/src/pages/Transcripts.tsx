import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { mockApiService } from '../services/mockApi';
import { Transcript } from '../types';
import { 
  Upload, 
  Play, 
  Download, 
  FileText, 
  Trash2, 
  Search,
  Filter,
  Plus,
  Check,
  ArrowLeft
} from 'lucide-react';
import FileUpload from '../components/FileUpload';
import TranscriptPlayer from '../components/TranscriptPlayer';

const Transcripts: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [filteredTranscripts, setFilteredTranscripts] = useState<Transcript[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [selectedTranscript, setSelectedTranscript] = useState<Transcript | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    fetchTranscripts();
  }, [user]);

  useEffect(() => {
    // Check if upload modal should be opened from URL parameter
    const shouldOpenUpload = searchParams.get('upload');
    if (shouldOpenUpload === 'true') {
      setShowUpload(true);
    }
  }, [searchParams]);

  useEffect(() => {
    filterTranscripts();
  }, [transcripts, searchQuery, statusFilter]);

  const fetchTranscripts = async () => {
    try {
      const data = await mockApiService.getTranscripts(user!.id, user!.role);
      setTranscripts(data);
    } catch (error) {
      console.error('Failed to fetch transcripts:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterTranscripts = () => {
    let filtered = transcripts;

    if (searchQuery) {
      filtered = filtered.filter(transcript =>
        transcript.fileName.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(transcript => transcript.status === statusFilter);
    }

    setFilteredTranscripts(filtered);
  };

  const handleFileUpload = async (file: File) => {
    try {
      const newTranscript = await mockApiService.uploadFile(file, user!.id);
      setTranscripts(prev => [newTranscript, ...prev]);
      setShowUpload(false);
    } catch (error) {
      console.error('Failed to upload file:', error);
    }
  };

  const handleAcceptTranscript = async (transcriptId: string) => {
    try {
      console.log('Accepting transcript:', transcriptId);
      await mockApiService.acceptTranscript(transcriptId);

      setTranscripts(prev => 
        prev.map(t => 
          t.id === transcriptId ? { ...t, accepted: true } : t
        )
      );
      setSelectedTranscript(null);
    } catch (error) {
      console.error('Failed to accept transcript:', error);
    }
  };

  const handleDownloadSrt = (transcript: Transcript) => {
    if (!transcript.srtUrl) return;
    
    // Create mock SRT content
    const srtContent = `1
00:00:00,000 --> 00:00:05,000
Welcome to our transcript service.

2
00:00:05,000 --> 00:00:10,000
This is a sample subtitle for ${transcript.fileName}.

3
00:00:10,000 --> 00:00:15,000
Thank you for using TranscribeAI.`;

    const blob = new Blob([srtContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${transcript.fileName.split('.')[0]}.srt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center justify-center w-10 h-10 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Transcripts</h1>
            <p className="mt-2 text-gray-600">
              Manage and view all your audio and video transcripts
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4 mr-2" />
          Upload File
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search transcripts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="pending">Pending</option>
                <option value="error">Error</option>
              </select>
            </div>
          </div>
          <div className="text-sm text-gray-500">
            {filteredTranscripts.length} of {transcripts.length} transcripts
          </div>
        </div>
      </div>

      {/* Transcripts List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        {filteredTranscripts.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-gray-900 mb-2">
              {transcripts.length === 0 ? 'No transcripts yet' : 'No matching transcripts'}
            </h3>
            <p className="text-gray-600 mb-6">
              {transcripts.length === 0 
                ? 'Upload your first audio or video file to get started'
                : 'Try adjusting your search or filter criteria'
              }
            </p>
            {transcripts.length === 0 && (
              <button
                onClick={() => setShowUpload(true)}
                className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Upload className="w-5 h-5 mr-2" />
                Upload Your First File
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredTranscripts.map((transcript) => (
              <div key={transcript.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4 flex-1 min-w-0 hover:cursor-pointer"  onClick={() => setSelectedTranscript(transcript)}>
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      {transcript.fileType === 'video' ? (
                        <Play className="w-6 h-6 text-blue-600" />
                      ) : (
                        <FileText className="w-6 h-6 text-blue-600" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 truncate">{transcript.fileName}</h3>
                      <div className="flex items-center space-x-4 mt-1">
                        <p className="text-sm text-gray-500">
                          {formatDate(transcript.createdAt)}
                        </p>
                        {transcript.duration && (
                          <p className="text-sm text-gray-500">
                            {Math.floor(transcript.duration / 60)}:{(transcript.duration % 60).toString().padStart(2, '0')}
                          </p>
                        )}
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(transcript.status)}`}>
                          {transcript.status.charAt(0).toUpperCase() + transcript.status.slice(1)}
                        </span>
                        {transcript.status === 'completed' && (
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            transcript.accepted 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {transcript.accepted ? 'Accepted' : 'Pending Review'}
                          </span>
                        )}
                      </div>
                      {transcript.status === 'processing' && transcript.progress !== undefined && (
                        <div className="mt-2 w-32">
                          <div className="bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${transcript.progress}%` }}
                            />
                          </div>
                          <p className="text-xs text-gray-500 mt-1">{transcript.progress}%</p>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 ml-4">
                    {transcript.status === 'completed' && (
                      <>
                        <button
                          onClick={() => setSelectedTranscript(transcript)}
                          className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Play with subtitles"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDownloadSrt(transcript)}
                          className="p-2 text-gray-600 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                          title="Download SRT"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      </>
                    )}
                    <button
                      className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* File Upload Modal */}
      {showUpload && (
        <FileUpload
          onUpload={handleFileUpload}
          onCancel={() => setShowUpload(false)}
        />
      )}

      {/* Transcript Player Modal */}
      {selectedTranscript && (
        <TranscriptPlayer
          transcript={selectedTranscript}
          onClose={() => setSelectedTranscript(null)}
          onAccept={handleAcceptTranscript}
        />
      )}
    </div>
  );
};

export default Transcripts;