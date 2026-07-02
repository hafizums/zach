import client from './client';

export const estimateVoiceover = async (projectId, providerName = 'mock', modelName = 'mock-audio', voiceId = null) => {
    const res = await client.post(`/api/projects/${projectId}/audio/voiceover/estimate`, {
        provider_name: providerName,
        model_name: modelName,
        voice_id: voiceId,
    });
    return res.data;
};

export const generateVoiceover = async (projectId, providerName = 'mock', modelName = 'mock-audio', voiceId = null, confirmed = false) => {
    const res = await client.post(`/api/projects/${projectId}/audio/voiceover/generate`, {
        provider_name: providerName,
        model_name: modelName,
        voice_id: voiceId,
        confirmed,
    });
    return res.data;
};

export const getActiveVoiceover = async (projectId) => {
    const res = await client.get(`/api/projects/${projectId}/audio/voiceover`);
    return res.data;
};

export const listProjectVoiceovers = async (projectId) => {
    const res = await client.get(`/api/projects/${projectId}/audio/voiceovers`);
    return res.data;
};
