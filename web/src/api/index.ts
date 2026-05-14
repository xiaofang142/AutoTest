import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

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
  parse: (pid: string, docIds?: string[]) =>
    api.post(`/projects/${pid}/documents/parse`, { document_ids: docIds }),
};

export const knowledgeApi = {
  get: (pid: string) => api.get(`/projects/${pid}/knowledge`),
  getRules: (pid: string, category?: string) =>
    api.get(`/projects/${pid}/knowledge/rules`, { params: { category } }),
};

export const scenarioApi = {
  list: (pid: string) => api.get(`/projects/${pid}/scenarios`),
  get: (id: string) => api.get(`/scenarios/${id}`),
  generate: (pid: string, platforms?: string[]) =>
    api.post(`/projects/${pid}/scenarios/generate`, { platforms }),
};

export const runApi = {
  get: (id: string) => api.get(`/runs/${id}`),
  create: (pid: string, data: any) => api.post(`/projects/${pid}/runs`, data),
  progress: (id: string) => api.get(`/runs/${id}/progress`),
  cancel: (id: string) => api.post(`/runs/${id}/cancel`),
  retry: (id: string, caseIds?: string[]) =>
    api.post(`/runs/${id}/retry`, { case_ids: caseIds }),
};

export const reportApi = {
  get: (id: string, format?: string) =>
    api.get(`/runs/${id}/report`, { params: { format } }),
};

export const defectApi = {
  list: (rid: string, severity?: string) =>
    api.get(`/runs/${rid}/defects`, { params: { severity } }),
  get: (id: string) => api.get(`/defects/${id}`),
  getEvidence: (id: string, format?: string) =>
    api.get(`/defects/${id}/evidence`, { params: { format } }),
};
