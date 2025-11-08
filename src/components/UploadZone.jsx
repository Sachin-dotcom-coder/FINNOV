// src/components/UploadZone.jsx
import { useCallback, useState, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { Upload, CheckCircle2, Loader, FileText, Folder, FolderOpen, X } from 'lucide-react';

const UploadZone = ({ onUploadComplete }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadMode, setUploadMode] = useState('files'); // 'files' or 'folder'
  const [selectedFiles, setSelectedFiles] = useState([]);
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // Supported file types
  const supportedFormats = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff'];

  const processFiles = useCallback((files) => {
    const validFiles = files.filter(file => {
      const extension = '.' + file.name.split('.').pop().toLowerCase();
      return supportedFormats.includes(extension);
    });

    const invalidFiles = files.length - validFiles.length;
    
    if (invalidFiles > 0) {
      alert(`${invalidFiles} file(s) were skipped. Only PDF, JPG, PNG, and TIFF files are supported.`);
    }

    setSelectedFiles(prev => {
      const newFiles = [...prev, ...validFiles];
      // Remove duplicates based on file name and size
      return newFiles.filter((file, index, self) => 
        index === self.findIndex(f => 
          f.name === file.name && f.size === file.size
        )
      );
    });
  }, []);

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files);
    processFiles(files);
    // Reset input to allow selecting same files again
    event.target.value = '';
  };

  const onDrop = useCallback((acceptedFiles) => {
    processFiles(acceptedFiles);
  }, [processFiles]);

  const startUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadProgress(0);

    // Simulate upload progress
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + 10;
      });
    }, 200);

    // Simulate AI processing
    setTimeout(() => {
      clearInterval(progressInterval);
      if (onUploadComplete) {
        onUploadComplete(selectedFiles);
      }
      setTimeout(() => {
        navigate('/dashboard');
      }, 1000);
    }, 2500);
  }, [selectedFiles, onUploadComplete, navigate]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.jpg', '.jpeg', '.png', '.tiff']
    },
    multiple: true
  });

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearAllFiles = () => {
    setSelectedFiles([]);
  };

  const getTotalSize = () => {
    const totalBytes = selectedFiles.reduce((sum, file) => sum + file.size, 0);
    return (totalBytes / (1024 * 1024)).toFixed(2);
  };

  // For folder upload simulation - user selects multiple files manually
  const simulateFolderUpload = () => {
    triggerFileInput();
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Upload Mode Toggle */}
      <div className="glass-panel rounded-2xl p-6 mb-6">
        <h2 className="text-2xl font-bold text-white mb-6">Upload Invoices</h2>
        
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => {
              setUploadMode('files');
              clearAllFiles();
            }}
            className={`flex-1 py-4 px-6 rounded-xl border-2 transition-all duration-300 flex flex-col items-center ${
              uploadMode === 'files'
                ? 'border-blue-500 bg-blue-500/20 text-white'
                : 'border-gray-600 text-gray-400 hover:border-gray-500'
            }`}
          >
            <FileText className="h-8 w-8 mb-3" />
            <span className="font-semibold text-lg">Individual Files</span>
            <p className="text-sm mt-2 opacity-80">Upload single invoice files</p>
          </button>
          
          <button
            onClick={() => {
              setUploadMode('folder');
              clearAllFiles();
            }}
            className={`flex-1 py-4 px-6 rounded-xl border-2 transition-all duration-300 flex flex-col items-center ${
              uploadMode === 'folder'
                ? 'border-green-500 bg-green-500/20 text-white'
                : 'border-gray-600 text-gray-400 hover:border-gray-500'
            }`}
          >
            <FolderOpen className="h-8 w-8 mb-3" />
            <span className="font-semibold text-lg">Multiple Files</span>
            <p className="text-sm mt-2 opacity-80">Upload multiple invoices at once</p>
          </button>
        </div>

        {/* Upload Area */}
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-300 cursor-pointer
            ${isDragActive
              ? 'border-blue-400 bg-blue-400/10'
              : 'border-gray-600 hover:border-gray-500 bg-gray-800/30'
            }
            ${isUploading ? 'pointer-events-none' : ''}
          `}
          onClick={uploadMode === 'folder' ? simulateFolderUpload : undefined}
        >
          <input {...getInputProps()} />
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.tiff"
            className="hidden"
          />
          
          <div className="transition-transform duration-300">
            {uploadMode === 'files' ? (
              <Upload className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            ) : (
              <Folder className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            )}
          </div>
          
          <h3 className="text-xl font-semibold text-white mb-2">
            {uploadMode === 'files' ? 'Select Invoice Files' : 'Select Multiple Invoices'}
          </h3>
          
          <p className="text-gray-400 mb-4">
            {uploadMode === 'files'
              ? 'Drag & drop files here or click to browse'
              : 'Click to select multiple invoice files'}
          </p>
          
          <p className="text-sm text-gray-500">
            Supported formats: PDF, JPG, PNG, TIFF
          </p>

          {uploadMode === 'folder' && (
            <p className="text-xs text-blue-400 mt-2">
              💡 Tip: Use Ctrl+A or Shift+Click to select multiple files
            </p>
          )}
        </div>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && !isUploading && (
        <div className="glass-panel rounded-2xl p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-xl font-semibold text-white">
                {uploadMode === 'folder' ? 'Selected Invoices' : 'Selected Files'}
              </h3>
              <p className="text-gray-400">
                {selectedFiles.length} file(s) • {getTotalSize()} MB total
              </p>
            </div>
            
            <button
              onClick={clearAllFiles}
              className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
            >
              Clear All
            </button>
          </div>
          
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {selectedFiles.map((file, index) => (
              <div
                key={`${file.name}-${file.size}-${index}`}
                className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <FileText className="h-5 w-5 text-blue-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">{file.name}</p>
                    <p className="text-gray-400 text-sm">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(index);
                  }}
                  className="p-2 hover:bg-red-500/20 rounded-lg transition-colors flex-shrink-0"
                >
                  <X className="h-4 w-4 text-red-400" />
                </button>
              </div>
            ))}
          </div>

          {/* Upload Button */}
          <button
            onClick={startUpload}
            className={`w-full mt-6 py-4 rounded-xl font-semibold text-lg transition-all duration-300 ${
              uploadMode === 'files'
                ? 'bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600'
                : 'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600'
            } text-white hover:scale-105`}
          >
            Process {selectedFiles.length} Invoice{selectedFiles.length !== 1 ? 's' : ''}
          </button>
        </div>
      )}

      {/* Upload Progress */}
      {isUploading && (
        <div className="glass-panel rounded-2xl p-6">
          <div className="space-y-6">
            <div className="relative">
              <Loader className="h-16 w-16 text-blue-400 animate-spin mx-auto" />
              <CheckCircle2 
                className={`h-16 w-16 text-green-400 absolute inset-0 mx-auto transition-all duration-500 ${
                  uploadProgress === 100 ? 'opacity-100 scale-100' : 'opacity-0 scale-50'
                }`}
              />
            </div>
            <div className="space-y-4">
              <h3 className="text-xl font-semibold text-white">
                {uploadProgress < 100 ? 'Analyzing with AI...' : 'Analysis Complete!'}
              </h3>
              <div className="w-full bg-gray-600 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-blue-400 to-green-400 h-3 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-sm text-gray-400">
                <span>Processing {selectedFiles.length} files...</span>
                <span className="font-mono">{uploadProgress}%</span>
              </div>
              <p className="text-gray-400">
                {uploadProgress < 100 
                  ? 'Extracting data and detecting anomalies...' 
                  : 'Redirecting to dashboard...'
                }
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UploadZone;