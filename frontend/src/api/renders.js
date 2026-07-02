import client from './client';

export const generateRender = async (projectId) => {
  const response = await client.post(`/projects/${projectId}/renders/generate`);
  return response.data;
};

export const getActiveRender = async (projectId) => {
  const response = await client.get(`/projects/${projectId}/renders/active`);
  return response.data;
};

export const listProjectRenders = async (projectId) => {
  const response = await client.get(`/projects/${projectId}/renders`);
  return response.data;
};

export const approveRender = async (projectId) => {
  const response = await client.post(`/projects/${projectId}/renders/approve`);
  return response.data;
};
