import axios from 'axios';
import type { Settings, TestConnectionResult } from '../types';

const api = axios.create({
  baseURL: 'http://localhost:8005',
  timeout: 30000,
});

export const apiService = {
  // ── Checklist ──
  uploadChecklist: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/api/checklist/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  pasteChecklist: async (text: string) => {
    const res = await api.post('/api/checklist/paste', { text });
    return res.data;
  },

  getChecklist: async (runId: string) => {
    const res = await api.get(`/api/checklist/${runId}`);
    return res.data;
  },

  confirmChecklist: async (runId: string, requirements: any[]) => {
    const res = await api.post(`/api/checklist/${runId}/confirm`, { requirements });
    return res.data;
  },

  // ── Repository ──
  browseFolder: async (): Promise<{ path: string | null }> => {
    const res = await api.post('/api/repository/browse-folder');
    return res.data;
  },

  scanRepository: async (path: string, runId?: string, useCache: boolean = true) => {
    const res = await api.post('/api/repository/scan', { run_id: runId || null, path, use_cache: useCache });
    return res.data;
  },

  getScanStatus: async (runId: string) => {
    const res = await api.get(`/api/repository/scan/${runId}/status`);
    return res.data;
  },

  cancelScan: async (runId: string) => {
    const res = await api.post(`/api/repository/scan/${runId}/cancel`);
    return res.data;
  },

  getRepositoryFiles: async (runId: string, page: number = 1, perPage: number = 100) => {
    const res = await api.get(`/api/repository/${runId}/files`, { params: { page, per_page: perPage } });
    return res.data;
  },

  // ── Validation ──
  runValidation: async (runId: string) => {
    const res = await api.post(`/api/validation/${runId}/start`);
    return res.data;
  },

  getValidationStatus: async (runId: string) => {
    const res = await api.get(`/api/validation/${runId}/status`);
    return res.data;
  },

  cancelValidation: async (runId: string) => {
    const res = await api.post(`/api/validation/${runId}/cancel`);
    return res.data;
  },

  getResults: async (runId: string) => {
    const res = await api.get(`/api/validation/${runId}/results`);
    return res.data;
  },

  getResultDetail: async (runId: string, reqId: string) => {
    const res = await api.get(`/api/validation/${runId}/result/${reqId}`);
    return res.data;
  },

  // ── Review ──
  submitManualReview: async (resultId: number, data: { new_status: string, reviewer_note: string }) => {
    const res = await api.post(`/api/review/${resultId}`, data);
    return res.data;
  },

  // ── Settings ──
  getSettings: async (): Promise<Settings> => {
    const res = await api.get('/api/settings');
    return res.data;
  },

  updateSettings: async (settings: Partial<Settings>) => {
    const res = await api.put('/api/settings', settings);
    return res.data;
  },

  testConnection: async (settings?: Partial<Settings>): Promise<TestConnectionResult> => {
    const res = await api.post('/api/settings/test-connection', settings || {});
    return res.data;
  },

  // ── History ──
  getHistory: async () => {
    const res = await api.get('/api/history');
    return res.data;
  },

  getRunDetail: async (runId: string) => {
    const res = await api.get(`/api/history/${runId}`);
    return res.data;
  },

  deleteRun: async (runId: string) => {
    const res = await api.delete(`/api/history/${runId}`);
    return res.data;
  },

  clearAllHistory: async () => {
    const res = await api.delete('/api/history');
    return res.data;
  },

  exportReport: async (runId: string, format: string) => {
    const res = await api.post(`/api/history/${runId}/export`, { format }, {
      responseType: format === 'json' ? 'json' : 'blob',
    });
    return res.data;
  },

  // ── Verification Engine ──
  runVerification: async (tool: string, args: Record<string, any>, sessionId?: string | null) => {
    const res = await api.post('/api/verification/run', {
      session_id: sessionId || null,
      tool,
      arguments: args,
    });
    return res.data;
  },

  getVerificationResult: async (sessionId: string) => {
    const res = await api.get(`/api/verification/result/${sessionId}`);
    return res.data;
  },

  browseVerificationFolder: async (): Promise<{ path: string | null }> => {
    const res = await api.post('/api/verification/browse');
    return res.data;
  },

  browseVerificationFile: async (): Promise<{ path: string | null; paths?: string[] }> => {
    const res = await api.post('/api/verification/browse-file');
    return res.data;
  },

  // ── Catalog Generator ──
  browseCatalogFolder: async (): Promise<{ path: string | null }> => {
    const res = await api.post('/api/catalog/browse-folder');
    return res.data;
  },

  scanCatalogFolder: async (folderPath: string, category: string = 'seismic') => {
    const res = await api.post('/api/catalog/scan-folder', { folder_path: folderPath, category });
    return res.data;
  },

  generateSeismicCatalog: async (catalogType: string, folderPath: string, params: Record<string, any>) => {
    const res = await api.post(
      '/api/catalog/generate/seismic',
      {
        catalog_type: catalogType,
        folder_path: folderPath,
        params,
      },
      { timeout: 0 }
    );
    return res.data;
  },

  generateSeismicCatalogStream: async (
    catalogType: string,
    folderPath: string,
    params: Record<string, any>,
    onProgress: (event: CatalogProgressEvent) => void
  ) => {
    return streamCatalogRequest(
      '/api/catalog/generate/seismic-stream',
      { catalog_type: catalogType, folder_path: folderPath, params },
      onProgress
    );
  },

  generateWellCatalog: async (catalogType: string, folderPath: string, params: Record<string, any>) => {
    const res = await api.post(
      '/api/catalog/generate/well',
      {
        catalog_type: catalogType,
        folder_path: folderPath,
        params,
      },
      { timeout: 0 }
    );
    return res.data;
  },

  generateWellCatalogStream: async (
    catalogType: string,
    folderPath: string,
    params: Record<string, any>,
    onProgress: (event: CatalogProgressEvent) => void
  ) => {
    return streamCatalogRequest(
      '/api/catalog/generate/well-stream',
      { catalog_type: catalogType, folder_path: folderPath, params },
      onProgress
    );
  },

  getCatalogDownloadUrl: (filePath: string) => {
    return `http://localhost:8005/api/catalog/download?file_path=${encodeURIComponent(filePath)}`;
  },
};

export interface CatalogProgressEvent {
  type: 'progress' | 'complete' | 'error';
  percent?: number;
  message?: string;
  current_file?: string;
  current_index?: number;
  total_files?: number;
  stage?: string;
  result?: any;
  error?: string;
}

async function streamCatalogRequest(
  endpoint: string,
  body: Record<string, any>,
  onProgress: (event: CatalogProgressEvent) => void
): Promise<any> {
  const baseURL = api.defaults.baseURL || 'http://localhost:8005';
  const response = await fetch(`${baseURL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let errDetail = 'Gagal memproses pembuatan catalog.';
    try {
      const errJson = await response.json();
      if (errJson?.detail) errDetail = errJson.detail;
    } catch {}
    throw new Error(errDetail);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('Response stream tidak tersedia.');

  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let finalResult: any = null;
  let serverError: string | null = null;

  const parseAndHandle = (rawLine: string) => {
    const trimmed = rawLine.trim();
    if (!trimmed) return;

    let data: CatalogProgressEvent;
    try {
      // Sanitize any NaN or Infinity that might have been emitted by legacy float values
      const safeJson = trimmed
        .replace(/:\s*NaN/g, ': null')
        .replace(/:\s*Infinity/g, ': null')
        .replace(/:\s*-Infinity/g, ': null');
      data = JSON.parse(safeJson);
    } catch (parseErr) {
      console.warn('Gagal membaca potongan log NDJSON:', trimmed.slice(0, 100), parseErr);
      return;
    }

    if (data.type === 'progress') {
      onProgress(data);
    } else if (data.type === 'complete') {
      finalResult = data.result;
    } else if (data.type === 'error') {
      serverError = data.error || 'Terjadi kesalahan saat memproses data katalog.';
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      parseAndHandle(line);
      if (serverError) {
        throw new Error(serverError);
      }
    }
  }

  if (buffer.trim()) {
    parseAndHandle(buffer);
  }

  if (serverError) {
    throw new Error(serverError);
  }

  if (!finalResult) {
    throw new Error('Proses pembuatan katalog selesai tanpa mengembalikan data hasil.');
  }

  return finalResult;
}

export default api;
