import apiClient from "./client";

export const createProject = async (projectData) => {
  const response = await apiClient.post("/api/projects/", projectData);
  return response.data;
};

export const listProjects = async () => {
  const response = await apiClient.get("/api/projects/");
  return response.data;
};

export const getProject = async (projectId) => {
  const response = await apiClient.get(`/api/projects/${projectId}`);
  return response.data;
};

export const updateProject = async (projectId, projectData) => {
  const response = await apiClient.patch(`/api/projects/${projectId}`, projectData);
  return response.data;
};

export const deleteProject = async (projectId) => {
  const response = await apiClient.delete(`/api/projects/${projectId}`);
  return response.data;
};
