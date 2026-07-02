import client from './client';

export const generateSubtitles = async (projectId) => {
    const res = await client.post(`/projects/${projectId}/subtitles/generate`);
    return res.data;
};

export const listProjectSubtitles = async (projectId) => {
    const res = await client.get(`/projects/${projectId}/subtitles`);
    return res.data;
};

export const listVoiceoverSubtitles = async (voiceoverId) => {
    const res = await client.get(`/voiceovers/${voiceoverId}/subtitles`);
    return res.data;
};

export const updateSubtitleSegment = async (segmentId, updateData) => {
    const res = await client.patch(`/subtitles/${segmentId}`, updateData);
    return res.data;
};

export const approveSubtitles = async (projectId) => {
    const res = await client.post(`/projects/${projectId}/subtitles/approve`);
    return res.data;
};
