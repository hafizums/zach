import client from './client';

export const generateVoiceover = async (projectId) => {
    const res = await client.post(`/projects/${projectId}/audio/voiceover/generate`);
    return res.data;
};

export const getActiveVoiceover = async (projectId) => {
    const res = await client.get(`/projects/${projectId}/audio/voiceover`);
    return res.data;
};

export const listProjectVoiceovers = async (projectId) => {
    const res = await client.get(`/projects/${projectId}/audio/voiceovers`);
    return res.data;
};
