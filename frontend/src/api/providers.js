import client from './client';

export const listProviderModels = async () => {
    const res = await client.get(`/api/providers/models`);
    return res.data;
};

export const listEnabledProviderModels = async () => {
    const res = await client.get(`/api/providers/models/enabled`);
    return res.data;
};

export const listProviderModelsByModality = async (modality) => {
    const res = await client.get(`/api/providers/models/modality/${modality}`);
    return res.data;
};

export const createProviderModel = async (data) => {
    const res = await client.post(`/api/providers/models`, data);
    return res.data;
};

export const updateProviderModel = async (modelId, data) => {
    const res = await client.patch(`/api/providers/models/${modelId}`, data);
    return res.data;
};

export const enableProviderModel = async (modelId) => {
    const res = await client.post(`/api/providers/models/${modelId}/enable`);
    return res.data;
};

export const disableProviderModel = async (modelId) => {
    const res = await client.post(`/api/providers/models/${modelId}/disable`);
    return res.data;
};

export const preflightProvider = async (data) => {
    const res = await client.post(`/api/providers/preflight`, data);
    return res.data;
};

export const listRecentProviderRuns = async () => {
    const res = await client.get(`/api/providers/runs/recent`);
    return res.data;
};

export const listProjectProviderRuns = async (projectId) => {
    const res = await client.get(`/api/projects/${projectId}/provider-runs`);
    return res.data;
};

export const listSceneProviderRuns = async (sceneId) => {
    const res = await client.get(`/api/scenes/${sceneId}/provider-runs`);
    return res.data;
};
