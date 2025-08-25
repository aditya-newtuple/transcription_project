import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { mockApiService } from '../services/mockApi';
import { getDiskSpace } from '../services/apiService';
import { DashboardStats, Transcript } from '../types';
import { 
  FileText, 
  Clock, 
  CheckCircle, 
  HardDrive,
  TrendingUp,
  Activity,
  Upload,
  Play,
  Users
} from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentTranscripts, setRecentTranscripts] = useState<Transcript[]>([]);
  const [loading, setLoading] = useState(true);
  const [diskSpace, setDiskSpace] = useState<{ used: number; total: number; percentage: number } | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dashboardStats, transcripts] = await Promise.all([
          mockApiService.getDashboardStats(user!.id, user!.role),
          mockApiService.getTranscripts(user!.id, user!.role)
        ]);
        
        setStats(dashboardStats);
        setRecentTranscripts(transcripts.slice(0, 5));
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  // Get disk space information from backend API
  useEffect(() => {
    const fetchDiskSpace = async () => {
      try {
        const diskData = await getDiskSpace();
        setDiskSpace({
          used: diskData.used_gb,
          total: diskData.total_gb,
          percentage: diskData.percentage
        });
      } catch (error) {
        console.error('Failed to fetch disk space:', error);
        // Fallback to mock data if API fails
        setDiskSpace({
          used: 250,
          total: 500,
          percentage: 50
        });
      }
    };

    fetchDiskSpace();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const statCards = [
    {
      name: 'Total Transcripts',
      value: stats?.totalTranscripts || 0,
      icon: FileText,
      color: 'bg-blue-500',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600'
    },
    {
      name: 'Pending Jobs',
      value: stats?.pendingJobs || 0,
      icon: Clock,
      color: 'bg-yellow-500',
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-600'
    },
    {
      name: 'Completed Jobs',
      value: stats?.completedJobs || 0,
      icon: CheckCircle,
      color: 'bg-green-500',
      bgColor: 'bg-green-50',
      textColor: 'text-green-600'
    },
    {
      name: 'Disk Space',
      value: diskSpace ? `${diskSpace.used}GB / ${diskSpace.total}GB` : 'Loading...',
      icon: HardDrive,
      color: 'bg-purple-500',
      bgColor: 'bg-purple-50',
      textColor: 'text-purple-600',
      subtitle: diskSpace ? `${diskSpace.percentage}% used` : ''
    }
  ];

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
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Welcome back, {user?.name}. Here's what's happening with your transcripts.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
                  {stat.subtitle && (
                    <p className="text-sm text-gray-500 mt-1">{stat.subtitle}</p>
                  )}
                </div>
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <Icon className={`w-6 h-6 ${stat.textColor}`} />
                </div>
              </div>
              {stat.name === 'Disk Space' && diskSpace && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                    <span>Used: {diskSpace.used}GB</span>
                    <span>Free: {diskSpace.total - diskSpace.used}GB</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        diskSpace.percentage > 80 ? 'bg-red-500' : 
                        diskSpace.percentage > 60 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${diskSpace.percentage}%` }}
                    />
                  </div>
                </div>
              )}
              {!stat.subtitle && stat.name !== 'Disk Space' && (
                <div className="mt-4 flex items-center">
                  <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                  <span className="text-sm text-green-600">+12% from last month</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Quick Actions</h2>
            <p className="text-sm text-gray-600 mt-1">Get started with common tasks</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/transcripts?upload=true"
            className="group relative p-6 bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-xl hover:from-blue-100 hover:to-blue-200 transition-all duration-200 hover:shadow-md"
          >
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
                <Upload className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">Upload New File</h3>
                <p className="text-sm text-gray-600 mt-1">Add audio or video for transcription</p>
              </div>
            </div>
            <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
            </div>
          </Link>

          <Link
            to="/transcripts"
            className="group relative p-6 bg-gradient-to-br from-green-50 to-green-100 border border-green-200 rounded-xl hover:from-green-100 hover:to-green-200 transition-all duration-200 hover:shadow-md"
          >
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 group-hover:text-green-700 transition-colors">View All Transcripts</h3>
                <p className="text-sm text-gray-600 mt-1">Browse and manage your files</p>
              </div>
            </div>
            <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="w-2 h-2 bg-green-600 rounded-full"></div>
            </div>
          </Link>

          {user?.role === 'admin' && (
            <Link
              to="/admin"
              className="group relative p-6 bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200 rounded-xl hover:from-purple-100 hover:to-purple-200 transition-all duration-200 hover:shadow-md"
            >
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
                  <Users className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 group-hover:text-purple-700 transition-colors">Manage Users</h3>
                  <p className="text-sm text-gray-600 mt-1">Admin user management</p>
                </div>
              </div>
              <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <div className="w-2 h-2 bg-purple-600 rounded-full"></div>
              </div>
            </Link>
          )}
        </div>
      </div>

      {/* Recent Transcripts */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Recent Transcripts</h2>
            <Link
              to="/transcripts"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              View all
            </Link>
          </div>
        </div>
        <div className="divide-y divide-gray-200">
          {recentTranscripts.length === 0 ? (
            <div className="p-6 text-center">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No transcripts yet</h3>
              <p className="text-gray-600 mb-4">
                Upload your first audio or video file to get started
              </p>
              <Link
                to="/transcripts?upload=true"
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload File
              </Link>
            </div>
          ) : (
            recentTranscripts.map((transcript) => (
              <div key={transcript.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      {transcript.fileType === 'video' ? (
                        <Play className="w-5 h-5 text-blue-600" />
                      ) : (
                        <FileText className="w-5 h-5 text-blue-600" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{transcript.fileName}</h3>
                      <p className="text-sm text-gray-500">
                        {formatDate(transcript.createdAt)}
                        {transcript.duration && ` • ${Math.floor(transcript.duration / 60)}:${(transcript.duration % 60).toString().padStart(2, '0')}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className={`px-3 py-1 text-xs font-medium rounded-full ${getStatusColor(transcript.status)}`}>
                      {transcript.status.charAt(0).toUpperCase() + transcript.status.slice(1)}
                    </span>
                    {transcript.status === 'processing' && transcript.progress && (
                      <div className="w-20">
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
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;