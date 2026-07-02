import apiClient from "./client";

export const generatePrompts = async (projectId) => {
  const response = await apiClient.post(`/api/projects/${projectId}/prompts/generate`, {});
  return response.data;
};

export const listProjectPrompts = async (projectId) => {
  const response = await apiClient.get(`/api/projects/${projectId}/prompts`);
  return response.data;
};

export const listScenePrompts = async (sceneId) => {
  const response = await apiClient.get(`/api/scenes/${sceneId}/prompts`);
  return response.data;
};

export const updateImagePrompt = async (promptId, data) => {
  const response = await apiClient.patch(`/api/image-prompts/${promptId}`, data);
  return response.data;
};

export const updateVideoPrompt = async (promptId, data) => {
  const response = await apiClient.patch(`/api/video-prompts/${promptId}`, data);
  return response.data;
};

export const approvePrompts = async (projectId) => {
  const response = await apiClient.post(`/api/projects/${projectId}/prompts/approve`);
  return response.data;
};
