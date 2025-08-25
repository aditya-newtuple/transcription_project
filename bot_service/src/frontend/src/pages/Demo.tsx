import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Upload, FileAudio, FileVideo, Loader2, CheckCircle, AlertCircle, Play, Pause, Volume2, Edit2, Check, X, Eye, Plus, Search, ChevronUp, ChevronDown, Download, Info, Trash2 } from 'lucide-react';
import { createJob, getJob, getFile, listFiles, deleteFile } from '../services/apiService';
import { CreateJobResponse, JobWithFiles, FileWithTranscripts, FileInfo } from '../types';

const Demo: React.FC = () => {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<'queued_at'>('queued_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<CreateJobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<FileWithTranscripts | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentSubtitle, setCurrentSubtitle] = useState<string>('');
  const [allSubtitles, setAllSubtitles] = useState<Array<{ start: number; end: number; text: string; index: number }>>([]);
  const [currentSubtitleIndex, setCurrentSubtitleIndex] = useState<number>(-1);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState<string>('');
  const [isVideo, setIsVideo] = useState(false);
  const [showPlayerModal, setShowPlayerModal] = useState(false);
  const [showDownloadDropdown, setShowDownloadDropdown] = useState(false);
  
  const audioRef = useRef<HTMLAudioElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const pollingIntervalRef = useRef<number | null>(null);

  // Fetch files on component mount
  useEffect(() => {
    fetchFiles();
  }, []);

  // Polling for files with queued/processing/running status
  useEffect(() => {
    const hasActiveFiles = files.some(file => 
      file.status === 'queued' || 
      file.status === 'processing' || 
      file.status === 'running'
    );
    
    if (hasActiveFiles) {
      pollingIntervalRef.current = setInterval(() => {
        fetchFiles();
      }, 3000); // Poll every 3 seconds
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [files]);

  const fetchFiles = async () => {
    try {
      const filesData = await listFiles(20);
      setFiles(filesData);
    } catch (err) {
      console.error('Failed to fetch files:', err);
    } finally {
      setLoading(false);
    }
  };

  // Parse SRT content and extract subtitles with timestamps
  const parseSRT = (srtContent: string) => {
    const subtitles: Array<{ start: number; end: number; text: string; index: number }> = [];
    const blocks = srtContent.trim().split('\n\n');
    
    blocks.forEach((block, index) => {
      const lines = block.split('\n');
      if (lines.length >= 3) {
        const timeLine = lines[1];
        const text = lines.slice(2).join('\n');
        
        const timeMatch = timeLine.match(/(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})/);
        if (timeMatch) {
          const startTime = parseInt(timeMatch[1]) * 3600 + parseInt(timeMatch[2]) * 60 + parseInt(timeMatch[3]) + parseInt(timeMatch[4]) / 1000;
          const endTime = parseInt(timeMatch[5]) * 3600 + parseInt(timeMatch[6]) * 60 + parseInt(timeMatch[7]) + parseInt(timeMatch[8]) / 1000;
          subtitles.push({ start: startTime, end: endTime, text, index: index + 1 });
        }
      }
    });
    
    return subtitles;
  };

  // Update current subtitle based on audio/video time
  useEffect(() => {
    if (currentFile && currentFile.transcripts.length > 0) {
      const srtTranscript = currentFile.transcripts.find(t => t.format === 'srt');
      if (srtTranscript) {
        const subtitles = parseSRT(srtTranscript.content);
        setAllSubtitles(subtitles);
        
        const currentSubIndex = subtitles.findIndex(sub => currentTime >= sub.start && currentTime <= sub.end);
        if (currentSubIndex !== -1) {
          setCurrentSubtitle(subtitles[currentSubIndex].text);
          setCurrentSubtitleIndex(currentSubIndex);
        } else {
          setCurrentSubtitle('');
          setCurrentSubtitleIndex(-1);
        }
      }
    }
  }, [currentTime, currentFile]);

  // Check if file is video when currentFile changes
  useEffect(() => {
    if (currentFile) {
      setIsVideo(currentFile.mime_type.startsWith('video/'));
    }
  }, [currentFile]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(files);
    setError(null);
    setUploadResult(null);
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select at least one file');
      return;
    }

    setIsUploading(true);
    setError(null);
    setUploadResult(null);

    try {
      const result = await createJob(1, selectedFiles);
      setUploadResult(result);
      setSelectedFiles([]);
      setShowUploadModal(false);
      // Refresh files list
      fetchFiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleViewFile = async (fileId: number) => {
    try {
      const fileData = await getFile(fileId);
      setCurrentFile(fileData);
      setShowPlayerModal(true);
    } catch (err) {
      console.error('Failed to fetch file details:', err);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const getFileIcon = (file: FileInfo) => {
    if (file.mime_type.startsWith('audio/')) return <FileAudio className="w-5 h-5 text-blue-500" />;
    if (file.mime_type.startsWith('video/')) return <FileVideo className="w-5 h-5 text-purple-500" />;
    return <FileAudio className="w-5 h-5 text-gray-500" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'succeeded':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'processing':
      case 'running':
        return 'bg-yellow-100 text-yellow-800';
      case 'queued':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleMediaTimeUpdate = () => {
    const mediaElement = isVideo ? videoRef.current : audioRef.current;
    if (mediaElement) {
      setCurrentTime(mediaElement.currentTime);
    }
  };

  const handleMediaSeeking = () => {
    // This will be called when user starts seeking
    console.log('Seeking started');
  };

  const handleMediaSeeked = () => {
    const mediaElement = isVideo ? videoRef.current : audioRef.current;
    if (mediaElement) {
      const newTime = mediaElement.currentTime;
      setCurrentTime(newTime);
      
      // Force update subtitle highlighting immediately after seeking
      setTimeout(() => {
        if (currentFile && currentFile.transcripts.length > 0) {
          const srtTranscript = currentFile.transcripts.find(t => t.format === 'srt');
          if (srtTranscript) {
            const subtitles = parseSRT(srtTranscript.content);
            const currentSubIndex = subtitles.findIndex(sub => newTime >= sub.start && newTime <= sub.end);
            if (currentSubIndex !== -1) {
              setCurrentSubtitle(subtitles[currentSubIndex].text);
              setCurrentSubtitleIndex(currentSubIndex);
            } else {
              setCurrentSubtitle('');
              setCurrentSubtitleIndex(-1);
            }
          }
        }
      }, 50); // Small delay to ensure seeking is complete
    }
  };

  const handleMediaPlay = () => {
    setIsPlaying(true);
  };

  const handleMediaPause = () => {
    setIsPlaying(false);
  };

  const togglePlayPause = () => {
    const mediaElement = isVideo ? videoRef.current : audioRef.current;
    if (mediaElement) {
      if (isPlaying) {
        mediaElement.pause();
      } else {
        mediaElement.play();
      }
    }
  };

  const handleMediaEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatSRTTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
  };

  const handleEditClick = (index: number, text: string) => {
    if (!isPlaying) {
      setEditingIndex(index);
      setEditText(text);
    }
  };

  const handleSaveEdit = () => {
    if (editingIndex !== null) {
      const updatedSubtitles = [...allSubtitles];
      updatedSubtitles[editingIndex] = {
        ...updatedSubtitles[editingIndex],
        text: editText
      };
      setAllSubtitles(updatedSubtitles);
      setEditingIndex(null);
      setEditText('');
    }
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditText('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  // Filter and sort files
  const filteredAndSortedFiles = useMemo(() => {
    let filtered = files.filter(file => {
      // Filter by search query (filename)
      const matchesSearch = file.source_name.toLowerCase().includes(searchQuery.toLowerCase());
      
      // Filter by status
      const matchesStatus = statusFilter === 'all' || file.status === statusFilter;
      
      return matchesSearch && matchesStatus;
    });

    filtered.sort((a, b) => {
      const aValue = new Date(a.queued_at).getTime();
      const bValue = new Date(b.queued_at).getTime();

      if (sortDirection === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return filtered;
  }, [files, searchQuery, statusFilter, sortDirection]);

  const currentFiles = filteredAndSortedFiles;

  const handleSort = () => {
    setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleStatusFilter = (status: string) => {
    setStatusFilter(status);
  };

  const handleDeleteFile = async (fileId: number, fileName: string) => {
    if (window.confirm(`Are you sure you want to delete "${fileName}"? This action cannot be undone.`)) {
      try {
        await deleteFile(fileId);
        // Refresh the files list after successful deletion
        fetchFiles();
      } catch (err) {
        console.error('Failed to delete file:', err);
        alert('Failed to delete file. Please try again.');
      }
    }
  };

  // Close download dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (!target.closest('.download-dropdown')) {
        setShowDownloadDropdown(false);
      }
    };

    if (showDownloadDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showDownloadDropdown]);

  const handleDownloadTranscript = (format: 'srt' | 'txt') => {
    if (currentFile && currentFile.transcripts.length > 0) {
      const transcript = currentFile.transcripts.find(t => t.format === format);
      if (transcript) {
        const blob = new Blob([transcript.content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentFile.source_name.split('.')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Files Management</h1>
        <p className="text-gray-600">
          View and manage your uploaded files and transcriptions.
        </p>
      </div>

      {/* Files Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Files</h2>
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Upload Files</span>
          </button>
        </div>

        {/* Search Bar */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center space-x-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search by filename..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => handleStatusFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
            >
              <option value="all">All Status</option>
              <option value="queued">Queued</option>
              <option value="processing">Processing</option>
              <option value="running">Running</option>
              <option value="succeeded">Succeeded</option>
              <option value="failed">Failed</option>
            </select>
            <button
              onClick={handleSort}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              title={`Sort by date (${sortDirection === 'asc' ? 'Oldest first' : 'Newest first'})`}
            >
              {sortDirection === 'asc' ? (
                <>
                  <ChevronUp className="w-4 h-4 text-gray-600" />
                  <span className="text-sm text-gray-700">Oldest first</span>
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4 text-gray-600" />
                  <span className="text-sm text-gray-700">Newest first</span>
                </>
              )}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-gray-400" />
            <p className="text-gray-500">Loading files...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">File</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {currentFiles.map((file) => (
                  <tr 
                    key={file.id} 
                    className={`${
                      file.status === 'succeeded' 
                        ? 'hover:bg-blue-50 cursor-pointer' 
                        : 'hover:bg-gray-50 cursor-default'
                    } transition-colors`}
                    onClick={() => {
                      if (file.status === 'succeeded') {
                        handleViewFile(file.id);
                      }
                    }}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {getFileIcon(file)}
                        <div className="ml-3">
                          <div className="text-sm font-medium text-gray-900">{file.source_name}</div>
                          <div className="text-sm text-gray-500">Job #{file.job_id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatFileSize(file.bytes)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(file.status)}`}>
                        {file.status}
                        {(file.status === 'queued' || file.status === 'processing' || file.status === 'running') && (
                          <Loader2 className="w-3 h-3 ml-1 animate-spin" />
                        )}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(file.queued_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center space-x-2">
                        {file.status === 'succeeded' ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleViewFile(file.id);
                            }}
                            className="text-blue-600 hover:text-blue-900 flex items-center space-x-1"
                          >
                            <Eye className="w-4 h-4" />
                            <span>View</span>
                          </button>
                        ) : file.status === 'failed' ? (
                          <div className="text-red-600 text-xs">
                            {file.message ? 'Error occurred' : 'Failed'}
                          </div>
                        ) : (
                          <div className="text-gray-400 text-xs">Processing...</div>
                        )}
                        
                        {/* Delete button - show for all files */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteFile(file.id, file.source_name);
                          }}
                          className="text-red-600 hover:text-red-900 flex items-center space-x-1"
                          title="Delete file"
                        >
                          <Trash2 className="w-4 h-4" />
                          <span>Delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>


        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
          <div className="relative mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Files</h3>
              
              {/* File Drop Zone */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
                <input
                  type="file"
                  multiple
                  accept="audio/*,video/*"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-gray-900 mb-1">
                    Drop files here or click to browse
                  </p>
                  <p className="text-xs text-gray-500">
                    Supports audio and video files up to 100MB each
                  </p>
                </label>
              </div>

              {/* Selected Files */}
              {selectedFiles.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Selected Files ({selectedFiles.length})</h4>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {selectedFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded text-xs">
                        <span className="truncate">{file.name}</span>
                        <button
                          onClick={() => removeFile(index)}
                          className="text-red-500 hover:text-red-700 ml-2"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-700 text-sm">{error}</p>
                </div>
              )}

              <div className="flex items-center justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  disabled={selectedFiles.length === 0 || isUploading}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                      Uploading...
                    </>
                  ) : (
                    'Upload'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Player Modal */}
      {showPlayerModal && currentFile && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className="relative mx-auto p-6 border w-full max-w-7xl shadow-lg rounded-md bg-white max-h-[95vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  {isVideo ? <FileVideo className="w-6 h-6 text-purple-500" /> : <FileAudio className="w-6 h-6 text-blue-500" />}
                  <h3 className="text-xl font-semibold text-gray-900">{currentFile.source_name}</h3>
                </div>
                <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                  currentFile.status === 'succeeded' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {currentFile.status}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="relative download-dropdown">
                  <button
                    onClick={() => setShowDownloadDropdown(!showDownloadDropdown)}
                    className="flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    title="Download transcript"
                  >
                    <Download className="w-4 h-4" />
                    <span className="text-sm">Download</span>
                    <ChevronDown className="w-4 h-4" />
                  </button>
                  
                  {/* Download Dropdown */}
                  {showDownloadDropdown && (
                    <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                      <div className="py-1">
                        <button
                          onClick={() => {
                            handleDownloadTranscript('srt');
                            setShowDownloadDropdown(false);
                          }}
                          className="flex items-center space-x-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                        >
                          <FileAudio className="w-4 h-4 text-blue-500" />
                          <span>Download SRT</span>
                        </button>
                        <button
                          onClick={() => {
                            handleDownloadTranscript('txt');
                            setShowDownloadDropdown(false);
                          }}
                          className="flex items-center space-x-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                        >
                          <FileAudio className="w-4 h-4 text-green-500" />
                          <span>Download TXT</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => setShowPlayerModal(false)}
                  className="text-gray-400 hover:text-gray-600 p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Media Player */}
              <div className="lg:col-span-2">
                <div className="bg-gray-50 rounded-lg p-4">
                  {isVideo ? (
                    <video
                      ref={videoRef}
                      onTimeUpdate={handleMediaTimeUpdate}
                      onSeeking={handleMediaSeeking}
                      onSeeked={handleMediaSeeked}
                      onPlay={handleMediaPlay}
                      onPause={handleMediaPause}
                      onEnded={handleMediaEnded}
                      className="w-full rounded-lg shadow-sm"
                      controls
                    >
                      <source src={`${import.meta.env.VITE_API_BASE_URL || 'http://0.0.0.0:8081/'}v1/api/files/${currentFile.id}/download`} type={currentFile.mime_type} />
                      Your browser does not support the video element.
                    </video>
                  ) : (
                    <audio
                      ref={audioRef}
                      onTimeUpdate={handleMediaTimeUpdate}
                      onSeeking={handleMediaSeeking}
                      onSeeked={handleMediaSeeked}
                      onPlay={handleMediaPlay}
                      onPause={handleMediaPause}
                      onEnded={handleMediaEnded}
                      className="w-full"
                      controls
                    >
                      <source src={`${import.meta.env.VITE_API_BASE_URL || 'http://0.0.0.0:8081/'}v1/api/files/${currentFile.id}/download`} type={currentFile.mime_type} />
                      Your browser does not support the audio element.
                    </audio>
                  )}

                  {/* Custom Controls */}
                  <div className="mt-4 flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <button
                        onClick={togglePlayPause}
                        className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                        <span className="text-sm font-medium">{isPlaying ? 'Pause' : 'Play'}</span>
                      </button>
                      <span className="text-sm text-gray-600 font-medium">
                        {formatTime(currentTime)} / {formatTime(isVideo ? (videoRef.current?.duration || 0) : (audioRef.current?.duration || 0))}
                      </span>
                    </div>
                  </div>

                  {/* Current Subtitle Display */}
                  {currentSubtitle && (
                    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-xs font-bold px-2 py-1 bg-blue-600 text-white rounded-full">
                          {currentSubtitleIndex !== -1 ? allSubtitles[currentSubtitleIndex]?.index : '?'}
                        </span>
                        <span className="text-xs text-blue-600 font-medium">
                          {currentSubtitleIndex !== -1 ? 
                            `${formatSRTTime(allSubtitles[currentSubtitleIndex]?.start || 0)} → ${formatSRTTime(allSubtitles[currentSubtitleIndex]?.end || 0)}` 
                            : ''
                          }
                        </span>
                      </div>
                      <p className="text-blue-900 font-medium leading-relaxed">
                        {currentSubtitle}
                      </p>
                    </div>
                  )}
                </div>

                {/* File Information */}
                <div className="mt-6 bg-white border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <Info className="w-5 h-5 text-blue-500" />
                    <h4 className="text-lg font-medium text-gray-900">File Information</h4>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500 font-medium">File Size</p>
                      <p className="text-gray-900">{formatFileSize(currentFile.bytes)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-medium">Type</p>
                      <p className="text-gray-900">{currentFile.mime_type}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-medium">Job ID</p>
                      <p className="text-gray-900">#{currentFile.job_id}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-medium">Created</p>
                      <p className="text-gray-900">{new Date(currentFile.queued_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Subtitles */}
              <div className="lg:col-span-1">
                <div className="bg-white border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between p-4 border-b border-gray-200">
                    <h4 className="text-lg font-medium text-gray-900">Subtitles</h4>
                    <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                      {allSubtitles.length} entries
                    </span>
                  </div>
                  
                  <div className="h-96 overflow-y-auto p-4">
                    {allSubtitles.length > 0 ? (
                      <div className="space-y-3">
                        {allSubtitles.map((subtitle, index) => (
                          <div
                            key={index}
                            className={`p-4 rounded-lg border transition-all duration-200 ${
                              index === currentSubtitleIndex
                                ? 'bg-blue-50 border-blue-300 shadow-md'
                                : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                            }`}
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-center space-x-2">
                                <span className={`text-xs font-bold px-2 py-1 rounded-full ${
                                  index === currentSubtitleIndex 
                                    ? 'bg-blue-600 text-white' 
                                    : 'bg-gray-300 text-gray-700'
                                }`}>
                                  {subtitle.index}
                                </span>
                                <button
                                  onClick={() => handleEditClick(index, subtitle.text)}
                                  disabled={isPlaying}
                                  className={`p-1.5 rounded-full transition-colors ${
                                    isPlaying 
                                      ? 'text-gray-300 cursor-not-allowed' 
                                      : index === currentSubtitleIndex 
                                        ? 'text-blue-600 hover:bg-blue-200' 
                                        : 'text-gray-400 hover:bg-gray-200'
                                  }`}
                                  title={isPlaying ? "Pause to edit" : "Edit subtitle"}
                                >
                                  <Edit2 className="w-3 h-3" />
                                </button>
                              </div>
                              <span className={`text-xs font-medium ${
                                index === currentSubtitleIndex ? 'text-blue-600' : 'text-gray-500'
                              }`}>
                                {formatSRTTime(subtitle.start)} → {formatSRTTime(subtitle.end)}
                              </span>
                            </div>
                            
                            {editingIndex === index ? (
                              <div className="space-y-3">
                                <textarea
                                  value={editText}
                                  onChange={(e) => setEditText(e.target.value)}
                                  onKeyDown={handleKeyPress}
                                  className="w-full p-3 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                  rows={3}
                                  autoFocus
                                />
                                <div className="flex items-center space-x-2">
                                  <button
                                    onClick={handleSaveEdit}
                                    className="flex items-center space-x-1 px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                                  >
                                    <Check className="w-3 h-3" />
                                    <span>Save</span>
                                  </button>
                                  <button
                                    onClick={handleCancelEdit}
                                    className="flex items-center space-x-1 px-3 py-1.5 text-xs bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                                  >
                                    <X className="w-3 h-3" />
                                    <span>Cancel</span>
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <p className={`text-sm leading-relaxed ${
                                index === currentSubtitleIndex ? 'text-blue-900 font-medium' : 'text-gray-700'
                              }`}>
                                {subtitle.text}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center text-gray-500 py-12">
                        <Volume2 className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p className="font-medium">No subtitles available</p>
                        <p className="text-sm">This file doesn't have any subtitle data</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Demo;
