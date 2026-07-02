import apiClient from "./client";

export const generateProjectImages = async (projectId) => {
  const response = await apiClient.post(`/api/projects/${projectId}/assets/images/generate`, {});
  return response.data;
};

export const generateProjectClips = async (projectId) => {
  const response = await apiClient.post(`/api/projects/${projectId}/assets/clips/generate`, {});
  return response.data;
};

export const retrySceneImage = async (sceneId) => {
  const response = await apiClient.post(`/api/scenes/${sceneId}/assets/image/retry`, {});
  return response.data;
};

export const retrySceneClip = async (sceneId) => {
  const response = await apiClient.post(`/api/scenes/${sceneId}/assets/clip/retry`, {});
  return response.data;
};

export const listProjectAssets = async (projectId) => {
  const response = await apiClient.get(`/api/projects/${projectId}/assets`);
  return response.data;
};

export const listSceneAssets = async (sceneId) => {
  const response = await apiClient.get(`/api/scenes/${sceneId}/assets`);
  return response.data;
};

export const approveAssets = async (projectId) => {
  const response = await apiClient.post(`/api/projects/${projectId}/assets/approve`, {});
  return response.data;
};
