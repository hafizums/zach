import apiClient from "./client";

export const generateScript = async (projectId) => {
  const response = await apiClient.post(`/api/projects/${projectId}/scripts/generate`, {});
  return response.data;
};

export const listProjectScripts = async (projectId) => {
  const response = await apiClient.get(`/api/projects/${projectId}/scripts`);
  return response.data;
};

export const getLatestScript = async (projectId) => {
  const response = await apiClient.get(`/api/projects/${projectId}/scripts/latest`);
  return response.data;
};

export const getScript = async (scriptId) => {
  const response = await apiClient.get(`/api/scripts/${scriptId}`);
  return response.data;
};

export const updateScript = async (scriptId, data) => {
  const response = await apiClient.patch(`/api/scripts/${scriptId}`, data);
  return response.data;
};

export const approveScript = async (scriptId) => {
  const response = await apiClient.post(`/api/scripts/${scriptId}/approve`);
  return response.data;
};
