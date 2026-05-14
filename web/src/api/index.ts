import axios from "axios";

// API base URL: use Vite proxy (default), or direct URL via env var
const BASE = import.meta.env.VITE_API_URL || "/api/v1";
const api = axios.create({ baseURL: BASE });

export const projectApi = {
  list: (status?: string) => api.get("/projects", { params: { status } }),
  get: (id: string) => api.get(`/projects/${id}`),
  create: (data: any) => api.post("/projects", data),
  update: (id: string, data: any) => api.put(`/projects/${id}`, data),
  delete: (id: string) => api.delete(`/projects/${id}`),
};

export const documentApi = {
  list: (pid: string) => api.get(`/projects/${pid}/documents`),
  add: (pid: string, data: any) => api.post(`/projects/${pid}/documents`, data),
  parse: (pid: string) => api.post(`/projects/${pid}/documents/parse`),
};

export const knowledgeApi = {
  get: (pid: string) => api.get(`/projects/${pid}/knowledge`),
  getRules: (pid: string, cat?: string) => api.get(`/projects/${pid}/knowledge/rules`, { params: { category: cat } }),
};

export const scenarioApi = {
  list: (pid: string) => api.get(`/projects/${pid}/scenarios`),
  get: (id: string) => api.get(`/scenarios/${id}`),
  generate: (pid: string, plats?: string[]) => api.post(`/projects/${pid}/scenarios/generate`, { platforms: plats }),
};

export const runApi = {
  get: (id: string) => api.get(`/runs/${id}`),
  create: (pid: string, data: any) => api.post(`/projects/${pid}/runs`, data),
  progress: (id: string) => api.get(`/runs/${id}/progress`),
  cancel: (id: string) => api.post(`/runs/${id}/cancel`),
  retry: (id: string, cids?: string[]) => api.post(`/runs/${id}/retry`, { case_ids: cids }),
  list: (pid: string) => api.get(`/projects/${pid}/runs`),
};

export const reportApi = {
  get: (id: string, fmt?: string) => api.get(`/runs/${id}/report`, { params: { format: fmt } }),
};

export const defectApi = {
  list: (rid: string, sev?: string) => api.get(`/runs/${rid}/defects`, { params: { severity: sev } }),
  get: (id: string) => api.get(`/defects/${id}`),
  getEvidence: (id: string) => api.get(`/defects/${id}/evidence`),
};
