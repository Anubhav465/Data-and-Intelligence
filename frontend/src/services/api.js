import axios from 'axios';

// Use environment variable for API URL (set via Vite)
// Default to localhost for development
const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

// ── Ask question (Olist or uploaded table) ─────────────────────────────────
export const askQuestion = async (question, tableNames = null) => {
  try {
    const payload = { question };
    // Send as array (multi-table); backend also accepts legacy table_name string
    if (tableNames && tableNames.length > 0) payload.table_names = tableNames;

    const response = await api.post('/ask', payload);
    return response.data;
  } catch (error) {
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail || error.response.data?.message || '';

      if (status === 422) throw new Error('Invalid question format. Please try rephrasing your question.');
      if (status === 400) throw new Error(detail || 'The query could not be processed. Please try a different question.');
      if (status === 500) {
        if (detail.toLowerCase().includes('timeout') || detail.toLowerCase().includes('timed out'))
          throw new Error('The AI took too long to respond. Please try again — simpler questions work faster.');
        throw new Error(detail || 'An internal server error occurred. Please try again.');
      }
      throw new Error(`Server error (${status}): ${detail || 'Unknown error'}`);
    }
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout'))
      throw new Error('Request timed out. The backend may be processing a complex query — please try again.');
    if (error.request)
      throw new Error("Couldn't reach the backend. Make sure the FastAPI server is running on http://localhost:8000.");
    throw new Error(error.message || 'An unexpected error occurred.');
  }
};

// ── Upload CSV file ────────────────────────────────────────────────────────
export const uploadCSV = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      const detail = error.response.data?.detail || '';
      throw new Error(detail || `Upload failed (${error.response.status})`);
    }
    if (error.code === 'ECONNABORTED') throw new Error('Upload timed out. Try a smaller file.');
    if (error.request) throw new Error("Couldn't reach the backend. Make sure the server is running.");
    throw new Error(error.message || 'Upload failed.');
  }
};

// ── List uploaded tables ───────────────────────────────────────────────────
export const listTables = async () => {
  try {
    const response = await api.get('/tables');
    return response.data.tables || [];
  } catch {
    return [];
  }
};

// ── Delete uploaded table ──────────────────────────────────────────────────
export const deleteTable = async (tableName) => {
  const response = await api.delete(`/tables/${tableName}`);
  return response.data;
};
