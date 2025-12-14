import React, { useState } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

// Removed - using config

interface OCRJob {
  file_id: string;
  filename: string;
  path: string;
  size: number;
  status: string;
  progress?: number;
  message?: string;
}

const OCRTab: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [publicationDate, setPublicationDate] = useState('1990-01-01');
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<OCRJob | null>(null);
  const [ocrStatus, setOcrStatus] = useState<OCRJob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [bulkMode, setBulkMode] = useState(false);
  const [bulkResults, setBulkResults] = useState<any>(null);
  const [extractedDate, setExtractedDate] = useState<string | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (bulkMode) {
      const files = Array.from(event.target.files || []);
      setSelectedFiles(files);
      setBulkResults(null);
    } else {
      const file = event.target.files?.[0];
      if (file) {
        setSelectedFile(file);
        setPreviewUrl(URL.createObjectURL(file));
        setUploadedFile(null);
        setOcrStatus(null);
        setExtractedDate(null);
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setExtractedDate(null);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await axios.post(`${API_BASE}/ocr/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadedFile(response.data);

      // Set extracted date if available
      if (response.data.extracted_date) {
        setExtractedDate(response.data.extracted_date);
        setPublicationDate(response.data.extracted_date);
      }

      alert(response.data.message || 'Newspaper image uploaded successfully!');
    } catch (error: any) {
      console.error('Upload error:', error);
      alert(error.response?.data?.detail || 'Failed to upload newspaper image');
    } finally {
      setUploading(false);
    }
  };

  const handleBulkUpload = async () => {
    if (selectedFiles.length === 0) return;

    setUploading(true);
    setBulkResults(null);
    try {
      const formData = new FormData();
      selectedFiles.forEach(file => {
        formData.append('files', file);
      });

      const response = await axios.post(`${API_BASE}/ocr/upload-bulk`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setBulkResults(response.data);
      alert(`${response.data.message}\n\nStarting OCR processing for all files...`);

      // Auto-process all uploaded files
      setProcessing(true);
      await handleBulkProcess(response.data.results);

    } catch (error: any) {
      console.error('Bulk upload error:', error);
      alert(error.response?.data?.detail || 'Failed to upload files');
    } finally {
      setUploading(false);
    }
  };

  const handleBulkProcess = async (uploadedFiles: any[]) => {
    let completed = 0;
    let failed = 0;

    for (const fileData of uploadedFiles) {
      if (fileData.status === 'uploaded' && fileData.file_id) {
        try {
          await axios.post(`${API_BASE}/ocr/process`, {
            file_id: fileData.file_id,
            file_path: fileData.path,
          });
          completed++;
          console.log(`✅ Processed: ${fileData.filename}`);
        } catch (error) {
          failed++;
          console.error(`❌ Failed: ${fileData.filename}`, error);
        }
      }
    }

    setProcessing(false);
    alert(`Batch processing complete!\n✅ Successful: ${completed}\n❌ Failed: ${failed}`);
  };

  const handleStartOCR = async () => {
    if (!uploadedFile) return;

    setProcessing(true);
    try {
      const response = await axios.post(`${API_BASE}/ocr/process`, {
        file_id: uploadedFile.file_id,
        publication_date: publicationDate,
      });

      setOcrStatus(response.data);

      // Start polling for status
      const intervalId = setInterval(async () => {
        try {
          const statusResponse = await axios.get(
            `${API_BASE}/ocr/status/${uploadedFile.file_id}`
          );
          setOcrStatus(statusResponse.data);

          if (statusResponse.data.status === 'completed' || statusResponse.data.status === 'failed') {
            clearInterval(intervalId);
            setProcessing(false);
          }
        } catch (error) {
          console.error('Status check error:', error);
        }
      }, 3000);

      // Clean up interval after 10 minutes
      setTimeout(() => clearInterval(intervalId), 600000);
    } catch (error) {
      console.error('OCR processing error:', error);
      alert('Failed to start OCR processing');
      setProcessing(false);
    }
  };

  return (
    <div className="ocr-view">
      <div className="ocr-header">
        <h2>📰 OCR Processing</h2>
        <p className="tagline">Upload newspaper images for text extraction and analysis</p>
      </div>

      <div className="mode-toggle">
        <button
          className={!bulkMode ? 'active' : ''}
          onClick={() => {
            setBulkMode(false);
            setSelectedFiles([]);
            setBulkResults(null);
          }}
        >
          📄 Single Upload
        </button>
        <button
          className={bulkMode ? 'active' : ''}
          onClick={() => {
            setBulkMode(true);
            setSelectedFile(null);
            setPreviewUrl(null);
          }}
        >
          📚 Bulk Upload (Up to 50)
        </button>
      </div>

      <div className="ocr-panel">
        <div className="upload-section">
          <div className="file-upload-area">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              id="ocr-file-input"
              style={{ display: 'none' }}
              multiple={bulkMode}
              {...(bulkMode ? { webkitdirectory: "", directory: "" } : {})}
            />
            <label htmlFor="ocr-file-input" className="upload-label">
              <div className="upload-icon">📄</div>
              <div className="upload-text">
                {bulkMode
                  ? selectedFiles.length > 0
                    ? `${selectedFiles.length} files selected from folder`
                    : '📁 Click to select a folder of newspaper images'
                  : selectedFile
                  ? selectedFile.name
                  : 'Click to select a newspaper image'}
              </div>
              <div className="upload-hint">{bulkMode ? 'Select a folder - all images will be processed automatically' : 'Supported: JPG, PNG, PDF'}</div>
            </label>
          </div>

          {uploadedFile && !bulkMode && (
            <div className="ocr-metadata">
              {extractedDate ? (
                <div className="auto-detected-date">
                  ✨ Auto-detected date: <strong>{extractedDate}</strong>
                </div>
              ) : (
                <div className="manual-date-entry">
                  <div className="warning-message">
                    ⚠️ Could not auto-detect date. Please enter manually:
                  </div>
                  <div className="metadata-field">
                    <label>📅 Publication Date</label>
                    <input
                      type="date"
                      value={publicationDate}
                      onChange={(e) => setPublicationDate(e.target.value)}
                      min="1990-01-01"
                      max="1992-12-31"
                      className="date-input"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {(selectedFile || selectedFiles.length > 0) && (
            <div className="upload-actions">
              {!bulkMode ? (
                <>
                  <button
                    onClick={handleUpload}
                    disabled={uploading || !!uploadedFile}
                    className="upload-btn"
                  >
                    {uploading ? '⏳ Uploading...' : uploadedFile ? '✅ Uploaded' : '📤 Upload Image'}
                  </button>

                  {uploadedFile && (
                    <button
                      onClick={handleStartOCR}
                      disabled={processing}
                      className="process-btn"
                    >
                      {processing ? '⏳ Processing...' : '🔄 Start OCR Processing'}
                    </button>
                  )}
                </>
              ) : (
                <button
                  onClick={handleBulkUpload}
                  disabled={uploading || selectedFiles.length === 0}
                  className="upload-btn"
                >
                  {uploading
                    ? '⏳ Uploading...'
                    : `📤 Upload ${selectedFiles.length} Images`}
                </button>
              )}
            </div>
          )}
        </div>

        {previewUrl && (
          <div className="preview-section">
            <h3>Preview</h3>
            <img src={previewUrl} alt="Newspaper preview" className="newspaper-preview-image" />
          </div>
        )}
      </div>

      {ocrStatus && (
        <div className="ocr-status">
          <h3>📊 Processing Status</h3>
          <div className="status-card">
            <div className="status-header">
              <span className={`status-badge ${ocrStatus.status}`}>
                {ocrStatus.status === 'processing' && '⏳'}
                {ocrStatus.status === 'completed' && '✅'}
                {ocrStatus.status === 'failed' && '❌'}
                {' '}
                {ocrStatus.status.toUpperCase()}
              </span>
              {ocrStatus.progress !== undefined && (
                <span className="progress-text">{ocrStatus.progress}%</span>
              )}
            </div>

            {ocrStatus.progress !== undefined && (
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${ocrStatus.progress}%` }}
                />
              </div>
            )}

            <div className="status-message">{ocrStatus.message}</div>

            {ocrStatus.status === 'processing' && (
              <div className="status-info">
                <p>⏱️ Estimated time: {uploadedFile?.status === 'processing' ? '5-10 minutes' : 'Calculating...'}</p>
              </div>
            )}

            {ocrStatus.status === 'completed' && (
              <div className="status-success">
                <p>✅ OCR processing completed successfully!</p>
                <p>The extracted articles have been added to the database and are now searchable.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {bulkResults && (
        <div className="bulk-results">
          <h3>📊 Bulk Upload Results</h3>
          <div className="bulk-summary">
            <div className="summary-stat success">
              <div className="stat-label">✅ Successful</div>
              <div className="stat-value">{bulkResults.successful}</div>
            </div>
            <div className="summary-stat failed">
              <div className="stat-label">❌ Failed</div>
              <div className="stat-value">{bulkResults.failed}</div>
            </div>
            <div className="summary-stat total">
              <div className="stat-label">📁 Total</div>
              <div className="stat-value">{bulkResults.total_files}</div>
            </div>
          </div>

          <div className="results-table">
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Status</th>
                  <th>Detected Date</th>
                  <th>Size</th>
                </tr>
              </thead>
              <tbody>
                {bulkResults.results.map((result: any, idx: number) => (
                  <tr key={idx} className={result.status}>
                    <td>{result.filename}</td>
                    <td>
                      <span className={`status-badge ${result.status}`}>
                        {result.status === 'uploaded' ? '✅ Uploaded' : '❌ Error'}
                      </span>
                    </td>
                    <td>{result.extracted_date || 'Not detected'}</td>
                    <td>{result.size ? `${(result.size / 1024).toFixed(1)} KB` : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="ocr-info">
        <h3>ℹ️ About OCR Processing</h3>
        <p>
          This tool allows you to upload newspaper images and extract text using Optical Character Recognition (OCR).
          The extracted text is then processed for:
        </p>
        <ul>
          <li>📝 Article extraction and segmentation</li>
          <li>🎯 Named entity recognition (people, organizations, locations)</li>
          <li>😊 Sentiment analysis</li>
          <li>🏷️ Topic classification</li>
        </ul>
        <p>
          <strong>Processing time:</strong> Typically 5-10 minutes per newspaper page depending on image quality and size.
        </p>
      </div>
    </div>
  );
};

export default OCRTab;
