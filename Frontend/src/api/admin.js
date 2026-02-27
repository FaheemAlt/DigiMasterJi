import apiClient from './axios';

/**
 * Admin API - Knowledge Base Management
 * Handles RAG document upload, vector search, and knowledge base management
 */

export const adminApi = {
  /**
   * Upload a PDF document for RAG ingestion
   * @param {File} file - PDF file to upload
   * @param {string} subject - Subject category (Physics, Chemistry, etc.)
   * @param {string} language - Document language code (en, hi, etc.)
   * @param {string[]} tags - Optional tags for filtering
   * @returns {Promise} - Upload response with chunks processed
   */
  uploadDocument: (file, subject, language = 'en', tags = []) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('subject', subject);
    formData.append('language', language);
    formData.append('tags', tags.join(','));

    return apiClient.post('/admin/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      // Increase timeout for large file uploads
      timeout: 120000, // 2 minutes
    });
  },

  /**
   * Perform semantic vector search in the knowledge base
   * @param {Object} params - Search parameters
   * @param {string} params.query - Search query text
   * @param {number} params.limit - Max results (1-20)
   * @param {string} params.subject - Optional subject filter
   * @param {string} params.language - Optional language filter
   * @returns {Promise} - Array of search results with scores
   */
  vectorSearch: ({ query, limit = 5, subject = null, language = null }) => {
    return apiClient.post('/admin/search', {
      query,
      limit,
      subject,
      language,
    });
  },

  /**
   * Get list of all uploaded documents
   * @returns {Promise} - List of documents with chunk counts
   */
  getDocuments: () => {
    return apiClient.get('/admin/documents');
  },

  /**
   * Get knowledge base statistics
   * @returns {Promise} - Stats including total chunks, subjects breakdown, etc.
   */
  getStats: () => {
    return apiClient.get('/admin/stats');
  },

  /**
   * Delete a document and all its chunks
   * @param {string} filename - The source filename to delete
   * @returns {Promise} - Deletion confirmation with chunks deleted count
   */
  deleteDocument: (filename) => {
    return apiClient.delete(`/admin/documents/${encodeURIComponent(filename)}`);
  },

  /**
   * Get RAG service information and configuration
   * @returns {Promise} - RAG config including model info, chunk settings
   */
  getRagInfo: () => {
    return apiClient.get('/admin/rag-info');
  },

  /**
   * Manually trigger Knowledge Base sync/ingestion
   * @returns {Promise} - { success, status, jobId, knowledgeBaseId }
   */
  triggerSync: () => {
    return apiClient.post('/admin/sync');
  },

  /**
   * List recent ingestion jobs with status
   * @param {number} limit - Max number of jobs to return (default 10)
   * @returns {Promise} - { success, jobs, knowledgeBaseId, dataSourceId, total }
   */
  listSyncJobs: (limit = 10) => {
    return apiClient.get('/admin/sync/jobs', { params: { limit } });
  },

  /**
   * Get detailed status of a specific ingestion job
   * @param {string} jobId - The ingestion job ID
   * @returns {Promise} - { success, jobId, status, statistics, startedAt, updatedAt, failureReasons }
   */
  getSyncJobStatus: (jobId) => {
    return apiClient.get(`/admin/sync/jobs/${jobId}`);
  },
};

/**
 * Subject options matching backend SubjectEnum
 */
export const SUBJECT_OPTIONS = [
  { value: 'Physics', label: 'Physics', emoji: '⚡' },
  { value: 'Chemistry', label: 'Chemistry', emoji: '🧪' },
  { value: 'Biology', label: 'Biology', emoji: '🧬' },
  { value: 'Mathematics', label: 'Mathematics', emoji: '📐' },
  { value: 'General Science', label: 'General Science', emoji: '🔬' },
  { value: 'Environmental Science', label: 'Environmental Science', emoji: '🌍' },
];

/**
 * Language options matching backend LanguageEnum
 */
export const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English', native: 'English' },
  { value: 'hi', label: 'Hindi', native: 'हिंदी' },
  { value: 'bn', label: 'Bengali', native: 'বাংলা' },
  { value: 'ta', label: 'Tamil', native: 'தமிழ்' },
  { value: 'te', label: 'Telugu', native: 'తెలుగు' },
  { value: 'mr', label: 'Marathi', native: 'मराठी' },
  { value: 'gu', label: 'Gujarati', native: 'ગુજરાતી' },
  { value: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ' },
  { value: 'ml', label: 'Malayalam', native: 'മലയാളം' },
  { value: 'pa', label: 'Punjabi', native: 'ਪੰਜਾਬੀ' },
];
