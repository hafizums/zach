import apiClient from "./client";

export const generateProjectImages = async (projectId, providerName = "mock", modelName = "mock-image", confirmed = false) => {
  const response = await apiClient.post(`/api/projects/${projectId}/assets/images/generate`, {
    provider_name: providerName,
    model_name: modelName,
    confirmed,
  });
  return response.data;
};

export const generateProjectClips = async (projectId) => {
  const response = await apiClient.post(`/api/projects/${projectId}/assets/clips/generate`, {});
  return response.data;
};

export const retrySceneImage = async (sceneId, providerName = "mock", modelName = "mock-image", confirmed = false) => {
  const response = await apiClient.post(`/api/scenes/${sceneId}/assets/image/retry`, {
    provider_name: providerName,
    model_name: modelName,
    confirmed,
  });
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

export const estimateProjectImages = async (projectId, providerName = "mock", modelName = "mock-image") => {
  const response = await apiClient.post(`/api/projects/${projectId}/assets/images/estimate`, {
    provider_name: providerName,
    model_name: modelName,
  });
  return response.data;
};

export const estimateSceneImageRetry = async (sceneId, providerName = "mock", modelName = "mock-image") => {
  const response = await apiClient.post(`/api/scenes/${sceneId}/assets/image/estimate`, {
    provider_name: providerName,
    model_name: modelName,
  });
  return response.data;
};
