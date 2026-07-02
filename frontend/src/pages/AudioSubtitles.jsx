import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getProject } from '../api/projects';
import { generateVoiceover, getActiveVoiceover } from '../api/audio';
import { generateSubtitles, listProjectSubtitles, updateSubtitleSegment, approveSubtitles } from '../api/subtitles';

const AudioSubtitles = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [voiceover, setVoiceover] = useState(null);
  const [subtitles, setSubtitles] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generatingVoiceover, setGeneratingVoiceover] = useState(false);
  const [generatingSubtitles, setGeneratingSubtitles] = useState(false);
  const [savingSubtitles, setSavingSubtitles] = useState({});
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const projData = await getProject(projectId);
      setProject(projData);

      try {
        const voData = await getActiveVoiceover(projectId);
        setVoiceover(voData);
        if (voData) {
            const subsData = await listProjectSubtitles(projectId);
            setSubtitles(subsData);
        }
      } catch (voErr) {
        if (voErr.response?.status !== 404) {
          throw voErr;
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateVoiceover = async () => {
    try {
      setGeneratingVoiceover(true);
      setError(null);
      const voData = await generateVoiceover(projectId);
      setVoiceover(voData);
      
      // Need to reload project state as well
      const projData = await getProject(projectId);
      setProject(projData);
      
      // clear old subtitles
      setSubtitles([]);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate voiceover");
    } finally {
      setGeneratingVoiceover(false);
    }
  };

  const handleGenerateSubtitles = async () => {
    try {
      setGeneratingSubtitles(true);
      setError(null);
      const subsData = await generateSubtitles(projectId);
      setSubtitles(subsData);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate subtitles");
    } finally {
      setGeneratingSubtitles(false);
    }
  };

  const handleSubtitleChange = (index, field, value) => {
    const updated = [...subtitles];
    if (field === 'start_time' || field === 'end_time') {
        updated[index][field] = parseFloat(value);
    } else {
        updated[index][field] = value;
    }
    setSubtitles(updated);
  };

  const handleSaveSubtitle = async (index) => {
    const segment = subtitles[index];
    try {
      setSavingSubtitles({ ...savingSubtitles, [index]: true });
      await updateSubtitleSegment(segment.id, {
        start_time: segment.start_time,
        end_time: segment.end_time,
        text: segment.text,
        style: segment.style
      });
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save subtitle");
    } finally {
      setSavingSubtitles({ ...savingSubtitles, [index]: false });
    }
  };

  const handleApprove = async () => {
    try {
      setApproving(true);
      setError(null);
      await approveSubtitles(projectId);
      navigate(`/projects/${projectId}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to approve");
    } finally {
      setApproving(false);
    }
  };

  if (loading) return <div className="p-8">Loading Audio & Subtitles...</div>;
  if (!project) return <div className="p-8 text-red-500">Project not found</div>;

  const validPriorStatuses = ["CLIPS_GENERATED", "VOICEOVER_READY", "SUBTITLES_READY", "FINAL_RENDER_READY"];
  const canGenerate = validPriorStatuses.includes(project.status);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center bg-gray-900 p-6 rounded-lg shadow-lg border border-gray-800">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Audio & Subtitles</h1>
          <p className="text-gray-400">Generate voiceover and edit subtitles.</p>
        </div>
        <button
          onClick={() => navigate(`/projects/${projectId}`)}
          className="text-gray-400 hover:text-white transition-colors"
        >
          Back to Project
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-500 p-4 rounded-lg">
          {error}
        </div>
      )}

      {!canGenerate ? (
        <div className="bg-gray-900 border border-gray-800 p-8 rounded-lg text-center">
            <h2 className="text-xl text-gray-300">Assets are not approved yet.</h2>
            <p className="text-gray-500 mt-2">Please approve image and clip assets before generating audio.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            <div className="lg:col-span-1 space-y-6">
                <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg shadow-lg">
                    <h2 className="text-xl font-bold text-white mb-4">Voiceover</h2>
                    
                    {voiceover ? (
                        <div className="space-y-4">
                            <div className="bg-gray-800 p-4 rounded-lg text-sm space-y-2">
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Status</span>
                                    <span className="text-white font-medium">{voiceover.status}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Duration</span>
                                    <span className="text-white font-medium">{voiceover.duration_seconds}s</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Job ID</span>
                                    <span className="text-gray-300 text-xs truncate max-w-[150px]">{voiceover.provider_job_id || "None"}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">File Path</span>
                                    <span className="text-gray-300 text-xs truncate max-w-[150px]" title={voiceover.file_url}>{voiceover.file_url}</span>
                                </div>
                            </div>
                            
                            <button
                                onClick={handleGenerateVoiceover}
                                disabled={generatingVoiceover}
                                className="w-full bg-gray-800 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg transition-colors border border-gray-700 disabled:opacity-50"
                            >
                                {generatingVoiceover ? 'Regenerating...' : 'Regenerate Voiceover'}
                            </button>
                        </div>
                    ) : (
                        <button
                            onClick={handleGenerateVoiceover}
                            disabled={generatingVoiceover}
                            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-4 rounded-lg transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                        >
                            {generatingVoiceover ? 'Generating...' : 'Generate Voiceover'}
                        </button>
                    )}
                </div>
            </div>

            <div className="lg:col-span-2 space-y-6">
                <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg shadow-lg">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-bold text-white">Subtitles</h2>
                        {voiceover && (
                            <button
                                onClick={handleGenerateSubtitles}
                                disabled={generatingSubtitles || !voiceover}
                                className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded-lg transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-50 text-sm"
                            >
                                {generatingSubtitles ? 'Generating...' : (subtitles.length > 0 ? 'Regenerate Subtitles' : 'Generate Subtitles')}
                            </button>
                        )}
                    </div>
                    
                    {!voiceover ? (
                        <div className="text-center py-8 text-gray-500">
                            Generate voiceover first to create subtitles.
                        </div>
                    ) : subtitles.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            No subtitles generated yet.
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {subtitles.map((sub, index) => (
                                <div key={sub.id} className="bg-gray-800 rounded-lg p-4 border border-gray-700 grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
                                    <div className="md:col-span-1 text-gray-500 font-mono text-sm pt-2">
                                        #{sub.index + 1}
                                    </div>
                                    <div className="md:col-span-2 space-y-2">
                                        <div>
                                            <label className="text-xs text-gray-500 block mb-1">Start (s)</label>
                                            <input 
                                                type="number" 
                                                step="0.1"
                                                value={sub.start_time}
                                                onChange={(e) => handleSubtitleChange(index, 'start_time', e.target.value)}
                                                className="w-full bg-gray-900 border border-gray-700 rounded p-1 text-sm text-white"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-gray-500 block mb-1">End (s)</label>
                                            <input 
                                                type="number" 
                                                step="0.1"
                                                value={sub.end_time}
                                                onChange={(e) => handleSubtitleChange(index, 'end_time', e.target.value)}
                                                className="w-full bg-gray-900 border border-gray-700 rounded p-1 text-sm text-white"
                                            />
                                        </div>
                                    </div>
                                    <div className="md:col-span-7">
                                        <label className="text-xs text-gray-500 block mb-1">Text</label>
                                        <textarea
                                            value={sub.text}
                                            onChange={(e) => handleSubtitleChange(index, 'text', e.target.value)}
                                            rows="3"
                                            className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-white resize-none"
                                        />
                                    </div>
                                    <div className="md:col-span-2 pt-5">
                                        <button
                                            onClick={() => handleSaveSubtitle(index)}
                                            disabled={savingSubtitles[index]}
                                            className="w-full bg-gray-700 hover:bg-gray-600 text-white font-medium py-2 px-3 rounded transition-colors text-sm disabled:opacity-50"
                                        >
                                            {savingSubtitles[index] ? 'Saving...' : 'Save Edit'}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                
                {voiceover && subtitles.length > 0 && (
                    <div className="flex justify-end pt-4">
                        <button
                            onClick={handleApprove}
                            disabled={approving}
                            className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-8 rounded-lg shadow-lg shadow-green-500/20 transition-colors disabled:opacity-50 text-lg"
                        >
                            {approving ? 'Approving...' : 'Approve Audio & Subtitles'}
                        </button>
                    </div>
                )}
            </div>
        </div>
      )}
    </div>
  );
};

export default AudioSubtitles;
