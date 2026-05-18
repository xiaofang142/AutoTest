import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL || '/api/v1';
const api = axios.create({ baseURL: BASE });

export interface CreateTaskParams {
  name: string;
  target_url: string;
  code_dir?: string;        // 项目源码目录路径
  mode?: 'quick' | 'document_driven' | 'mixed';
  goal?: string;
  depth?: string;
  project_id?: string;
  doc_ids?: string[];
  description?: string;
}

export async function createTask(params: CreateTaskParams) {
  const formData = new URLSearchParams();
  formData.append('name', params.name);
  if (params.target_url) formData.append('target_url', params.target_url);
  if (params.mode) formData.append('mode', params.mode);
  if (params.project_id) formData.append('project_id', params.project_id);
  if (params.description) formData.append('description', params.description);
  const resp = await api.post('/tasks', formData.toString(), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return resp.data;
}

export async function listTasks(params?: { project_id?: string; status?: string; page?: number }) {
  const resp = await api.get('/tasks', { params });
  return resp.data;
}

export async function getTask(taskId: string) {
  const resp = await api.get(`/tasks/${taskId}`);
  return resp.data;
}

export async function startTask(taskId: string) {
  const resp = await api.post(`/tasks/${taskId}/start`);
  return resp.data;
}

export async function cancelTask(taskId: string) {
  const resp = await api.post(`/tasks/${taskId}/cancel`);
  return resp.data;
}

export async function getTaskTimeline(taskId: string) {
  const resp = await api.get(`/tasks/${taskId}/timeline`);
  return resp.data;
}

export async function getTaskDelivery(taskId: string) {
  const resp = await api.get(`/tasks/${taskId}/delivery`);
  return resp.data;
}

export async function getTaskRepairContext(taskId: string) {
  const resp = await api.get(`/tasks/${taskId}/repair-context`);
  return resp.data;
}
