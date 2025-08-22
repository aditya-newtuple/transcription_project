import React, { useState, useRef } from 'react';
import { Upload, X, FileAudio, FileVideo, AlertCircle } from 'lucide-react';

interface FileUploadProps {
  onUpload: (file: File) => void;
  onCancel: () => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUpload, onCancel }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const acceptedTypes = {
    'audio/mp3': '.mp3',
    'audio/wav': '.mpeg',
    'audio/m4a': '.mpeg4',
    'video/mp4': '.mp4',
  };

  const maxSize = 100 * 1024 * 1024; // 100MB

  const validateFile = (file: File): string | null => {
    if (!Object.keys(acceptedTypes).includes(file.type)) {
      return 'File type not supported. Please upload MP3, WAV, M4A, MP4, WebM, or MOV files.';
    }
    if (file.size > maxSize) {
      return 'File size too large. Please upload files smaller than 100MB.';
    }
    return null;
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  };

  const handleFileSelection = (file: File) => {
    setError('');
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }
    setSelectedFile(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      handleFileSelection(files[0]);
    }
  };



  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    try {
      await onUpload(selectedFile);
    } catch (error) {
      setError('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const isVideo = selectedFile?.type.startsWith('video/');

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Upload File</h2>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto">
          {!selectedFile ? (
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              className={`
                border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer
                ${dragOver 
                  ? 'border-blue-400 bg-blue-50' 
                  : 'border-gray-300 hover:border-gray-400'
                }
              `}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className={`w-16 h-16 mx-auto mb-4 ${dragOver ? 'text-blue-500' : 'text-gray-400'}`} />
              <h3 className="text-xl font-medium text-gray-900 mb-2">
                Drop your file here, or click to browse
              </h3>
              <p className="text-gray-500 mb-4">
                Support for mp4, mpeg, mp3,mpeg4
              </p>
              <div className="flex flex-wrap justify-center gap-2 text-xs text-gray-400">
                {Object.values(acceptedTypes).map((ext, index) => (
                  <span key={index} className="px-2 py-1 bg-gray-100 rounded">
                    {ext.toUpperCase()}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* File Info */}
              <div className="flex items-start space-x-4 p-4 bg-gray-50 rounded-xl">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  {isVideo ? (
                    <FileVideo className="w-6 h-6 text-blue-600" />
                  ) : (
                    <FileAudio className="w-6 h-6 text-blue-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-gray-900 truncate">{selectedFile.name}</h3>
                  <p className="text-sm text-gray-500">
                    {formatFileSize(selectedFile.size)} • {selectedFile.type}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="p-1 hover:bg-gray-200 rounded transition-colors"
                >
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>



              {/* Processing Info */}
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-medium text-blue-900 mb-2">What happens next?</h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• Your file will be processed using advanced AI</li>
                  <li>• Processing time depends on file length (typically 1-5 minutes)</li>
                  <li>• You'll receive an SRT subtitle file for download</li>
                  <li>• The transcript will be available for viewing and editing</li>
                </ul>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center">
              <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
              <span className="text-red-700 text-sm">{error}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end space-x-4 p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onCancel}
            className="px-6 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Processing...
              </div>
            ) : (
              'Start Transcription'
            )}
          </button>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept={Object.keys(acceptedTypes).join(',')}
          onChange={handleFileInputChange}
          className="hidden"
        />
      </div>
    </div>
  );
};

export default FileUpload;