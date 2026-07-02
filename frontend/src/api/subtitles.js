import client from './client';

export const estimateSubtitles = async (projectId, providerName = 'mock', modelName = 'mock-transcription') => {
    const res = await client.post(`/api/projects/${projectId}/subtitles/estimate`, {
        provider_name: providerName,
        model_name: modelName,
    });
    return res.data;
};

export const generateSubtitles = async (projectId, providerName = 'mock', modelName = 'mock-transcription', confirmed = false) => {
    const res = await client.post(`/api/projects/${projectId}/subtitles/generate`, {
        provider_name: providerName,
        model_name: modelName,
        confirmed,
    });
    return res.data;
};

export const listProjectSubtitles = async (projectId) => {
    const res = await client.get(`/api/projects/${projectId}/subtitles`);
    return res.data;
};

export const listVoiceoverSubtitles = async (voiceoverId) => {
    const res = await client.get(`/api/voiceovers/${voiceoverId}/subtitles`);
    return res.data;
};

export const updateSubtitleSegment = async (segmentId, updateData) => {
    const res = await client.patch(`/api/subtitles/${segmentId}`, updateData);
    return res.data;
};

export const approveSubtitles = async (projectId) => {
    const res = await client.post(`/api/projects/${projectId}/subtitles/approve`);
    return res.data;
};
