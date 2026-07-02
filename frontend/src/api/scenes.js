import apiClient from "./client";

export const generateScenes = async (projectId, options = {}) => {
  const response = await apiClient.post(`/api/projects/${projectId}/scenes/generate`, options);
  return response.data;
};

export const listProjectScenes = async (projectId) => {
  const response = await apiClient.get(`/api/projects/${projectId}/scenes`);
  return response.data;
};

export const listScriptScenes = async (scriptId) => {
  const response = await apiClient.get(`/api/scripts/${scriptId}/scenes`);
  return response.data;
};

export const getScene = async (sceneId) => {
  const response = await apiClient.get(`/api/scenes/${sceneId}`);
  return response.data;
};

export const updateScene = async (sceneId, data) => {
  const response = await apiClient.patch(`/api/scenes/${sceneId}`, data);
  return response.data;
};

export const approveScenePlan = async (projectId) => {
  const response = await apiClient.post(`/api/projects/${projectId}/scenes/approve`);
  return response.data;
};
