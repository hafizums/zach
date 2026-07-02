import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getProject } from '../api/projects';
import { generateRender, getActiveRender, approveRender } from '../api/renders';

const FinalRender = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [activeRender, setActiveRender] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, [projectId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const proj = await getProject(projectId);
      setProject(proj);

      try {
        const render = await getActiveRender(projectId);
        setActiveRender(render);
      } catch (e) {
        if (e.response && e.response.status !== 404) {
          console.error("Error loading active render:", e);
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load project details");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      const newRender = await generateRender(projectId);
      setActiveRender(newRender);
      
      const proj = await getProject(projectId);
      setProject(proj);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate mock render");
    } finally {
      setGenerating(false);
    }
  };

  const handleApprove = async () => {
    try {
      setApproving(true);
      setError(null);
      await approveRender(projectId);
      navigate(`/projects/${projectId}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to approve final render");
    } finally {
      setApproving(false);
    }
  };

  if (loading) return <div className="p-8">Loading Final Render...</div>;
  if (!project) return <div className="p-8 text-red-500">Project not found</div>;

  const validStatuses = ["SUBTITLES_READY", "FINAL_RENDER_READY"];
  const canGenerate = validStatuses.includes(project.status);

  let manifest = null;
  if (activeRender?.manifest_json) {
    try {
        manifest = JSON.parse(activeRender.manifest_json);
    } catch (e) {}
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center bg-gray-900 p-6 rounded-lg shadow-lg border border-gray-800">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Final Render Pipeline</h1>
          <p className="text-gray-400">Assemble assets, audio, and subtitles into a final video manifest.</p>
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
            <h2 className="text-xl text-gray-300">Subtitles are not approved yet.</h2>
            <p className="text-gray-500 mt-2">Please approve subtitles before generating the final render.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            <div className="lg:col-span-1 space-y-6">
                <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg shadow-lg">
                    <h2 className="text-xl font-bold text-white mb-4">Render Controls</h2>
                    
                    {activeRender ? (
                        <div className="space-y-4">
                            <div className="bg-gray-800 p-4 rounded-lg text-sm space-y-2">
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Status</span>
                                    <span className="text-white font-medium">{activeRender.status}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Duration</span>
                                    <span className="text-white font-medium">{activeRender.duration_seconds}s</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Resolution</span>
                                    <span className="text-gray-300">{activeRender.width}x{activeRender.height} ({activeRender.aspect_ratio})</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Output</span>
                                    <span className="text-gray-300 text-xs truncate max-w-[150px]" title={activeRender.output_url}>{activeRender.output_url}</span>
                                </div>
                            </div>
                            
                            <button
                                onClick={handleGenerate}
                                disabled={generating}
                                className="w-full bg-gray-800 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg transition-colors border border-gray-700 disabled:opacity-50"
                            >
                                {generating ? 'Rendering...' : 'Regenerate Mock Render'}
                            </button>
                        </div>
                    ) : (
                        <button
                            onClick={handleGenerate}
                            disabled={generating}
                            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-4 rounded-lg transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                        >
                            {generating ? 'Rendering...' : 'Generate Mock Render'}
                        </button>
                    )}
                </div>
            </div>

            <div className="lg:col-span-2 space-y-6">
                <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg shadow-lg">
                    <h2 className="text-xl font-bold text-white mb-6">Render Manifest Summary</h2>
                    
                    {!activeRender ? (
                        <div className="text-center py-8 text-gray-500">
                            Generate a mock render to view the assembly manifest.
                        </div>
                    ) : !manifest ? (
                        <div className="text-center py-8 text-red-500">
                            Failed to parse manifest data.
                        </div>
                    ) : (
                        <div className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-gray-800 p-4 rounded-lg">
                                    <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">Clips Configured</div>
                                    <div className="text-2xl font-bold text-white">{manifest.clips?.length || 0}</div>
                                </div>
                                <div className="bg-gray-800 p-4 rounded-lg">
                                    <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">Subtitles</div>
                                    <div className="text-2xl font-bold text-white">{manifest.subtitles?.length || 0} Segments</div>
                                </div>
                            </div>

                            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                                <h3 className="text-sm font-semibold text-gray-300 mb-3">Audio Source</h3>
                                <div className="text-sm text-gray-400 break-all font-mono bg-gray-900 p-2 rounded">
                                    {manifest.voiceover?.file_url}
                                </div>
                            </div>

                            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                                <h3 className="text-sm font-semibold text-gray-300 mb-3">Manifest Preview (JSON)</h3>
                                <pre className="text-xs text-gray-400 font-mono overflow-auto max-h-64 bg-gray-900 p-4 rounded border border-gray-700">
                                    {JSON.stringify(manifest, null, 2)}
                                </pre>
                            </div>
                        </div>
                    )}
                </div>
                
                {activeRender && (
                    <div className="flex justify-end pt-4">
                        <button
                            onClick={handleApprove}
                            disabled={approving}
                            className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-8 rounded-lg shadow-lg shadow-green-500/20 transition-colors disabled:opacity-50 text-lg"
                        >
                            {approving ? 'Finalizing...' : 'Approve & Finalize Render'}
                        </button>
                    </div>
                )}
            </div>
        </div>
      )}
    </div>
  );
};

export default FinalRender;
