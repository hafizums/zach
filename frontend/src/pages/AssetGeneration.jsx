import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getProject } from "../api/projects";
import {
  listProjectAssets,
  generateProjectImages,
  generateProjectClips,
  retrySceneImage,
  retrySceneClip,
  approveAssets,
  estimateProjectImages,
  estimateSceneImageRetry,
  estimateProjectClips,
  estimateSceneClipRetry,
} from "../api/assets";
import { listEnabledProviderModels } from "../api/providers";

const AssetGeneration = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [assetPairs, setAssetPairs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [retryErrors, setRetryErrors] = useState({});

  const [imageModels, setImageModels] = useState([]);
  const [selectedImageProvider, setSelectedImageProvider] = useState("mock");
  const [selectedImageModel, setSelectedImageModel] = useState("mock-image");

  const [videoModels, setVideoModels] = useState([]);
  const [selectedVideoProvider, setSelectedVideoProvider] = useState("mock");
  const [selectedVideoModel, setSelectedVideoModel] = useState("mock-video");

  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState(null);

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const proj = await getProject(projectId);
      setProject(proj);

      const loadedPairs = await listProjectAssets(projectId);
      setAssetPairs(loadedPairs);

      const allEnabled = await listEnabledProviderModels();
      const images = allEnabled.filter(m => m.modality === "image");
      setImageModels(images);
      if (images.length > 0) {
        setSelectedImageProvider(images[0].provider_name);
        setSelectedImageModel(images[0].model_name);
      }

      const videos = allEnabled.filter(m => m.modality === "video");
      setVideoModels(videos);
      if (videos.length > 0) {
        setSelectedVideoProvider(videos[0].provider_name);
        setSelectedVideoModel(videos[0].model_name);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load asset data");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateImages = async () => {
    setError(null);
    setRetryErrors({});
    try {
      setGenerating(true);
      const estimate = await estimateProjectImages(projectId, selectedImageProvider, selectedImageModel);
      if (estimate.requires_confirmation) {
        setConfirmModal({
          type: "project",
          estimate,
          onConfirm: async () => {
            setConfirmModal(null);
            await doGenerateImages();
          },
          onCancel: () => setConfirmModal(null),
        });
        setGenerating(false);
        return;
      }
      await doGenerateImages();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to estimate image generation");
      setGenerating(false);
    }
  };

  const doGenerateImages = async () => {
    try {
      setGenerating(true);
      setError(null);
      const newPairs = await generateProjectImages(projectId, selectedImageProvider, selectedImageModel, true);
      setAssetPairs(newPairs);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate images");
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateClips = async () => {
    setError(null);
    setRetryErrors({});
    try {
      setGenerating(true);
      const estimate = await estimateProjectClips(projectId, selectedVideoProvider, selectedVideoModel);
      if (estimate.requires_confirmation) {
        setConfirmModal({
          type: "project-clips",
          estimate,
          onConfirm: async () => {
            setConfirmModal(null);
            await doGenerateClips();
          },
          onCancel: () => setConfirmModal(null),
        });
        setGenerating(false);
        return;
      }
      await doGenerateClips();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to estimate clip generation");
      setGenerating(false);
    }
  };

  const doGenerateClips = async () => {
    try {
      setGenerating(true);
      setError(null);
      const newPairs = await generateProjectClips(projectId, selectedVideoProvider, selectedVideoModel, true);
      setAssetPairs(newPairs);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate clips");
    } finally {
      setGenerating(false);
    }
  };

  const handleRetryImage = async (sceneId) => {
    setRetryErrors(prev => ({ ...prev, [sceneId]: null }));
    try {
      setGenerating(true);
      const estimate = await estimateSceneImageRetry(sceneId, selectedImageProvider, selectedImageModel);
      if (estimate.requires_confirmation) {
        setConfirmModal({
          type: "retry",
          sceneId,
          estimate,
          onConfirm: async () => {
            setConfirmModal(null);
            await doRetryImage(sceneId);
          },
          onCancel: () => setConfirmModal(null),
        });
        setGenerating(false);
        return;
      }
      await doRetryImage(sceneId);
    } catch (err) {
      setRetryErrors(prev => ({ ...prev, [sceneId]: err.response?.data?.detail || "Failed to estimate retry" }));
      setGenerating(false);
    }
  };

  const doRetryImage = async (sceneId) => {
    try {
      setGenerating(true);
      const updatedPair = await retrySceneImage(sceneId, selectedImageProvider, selectedImageModel, true);
      setAssetPairs(prev => prev.map(p => p.scene_id === sceneId ? updatedPair : p));
    } catch (err) {
      setRetryErrors(prev => ({
        ...prev,
        [sceneId]: err.response?.data?.detail || "Failed to retry image",
      }));
    } finally {
      setGenerating(false);
    }
  };

  const handleRetryClip = async (sceneId) => {
    setRetryErrors(prev => ({ ...prev, [sceneId]: null }));
    try {
      setGenerating(true);
      const estimate = await estimateSceneClipRetry(sceneId, selectedVideoProvider, selectedVideoModel);
      if (estimate.requires_confirmation) {
        setConfirmModal({
          type: "retry-clip",
          sceneId,
          estimate,
          onConfirm: async () => {
            setConfirmModal(null);
            await doRetryClip(sceneId);
          },
          onCancel: () => setConfirmModal(null),
        });
        setGenerating(false);
        return;
      }
      await doRetryClip(sceneId);
    } catch (err) {
      setRetryErrors(prev => ({
        ...prev,
        [sceneId]: err.response?.data?.detail || "Failed to estimate clip retry",
      }));
      setGenerating(false);
    }
  };

  const doRetryClip = async (sceneId) => {
    try {
      setGenerating(true);
      const updatedPair = await retrySceneClip(sceneId, selectedVideoProvider, selectedVideoModel, true);
      setAssetPairs(prev => prev.map(p => p.scene_id === sceneId ? updatedPair : p));
    } catch (err) {
      setRetryErrors(prev => ({
        ...prev,
        [sceneId]: err.response?.data?.detail || "Failed to retry clip",
      }));
    } finally {
      setGenerating(false);
    }
  };

  const handleApproveAll = async () => {
    if (!window.confirm("Are you sure you want to approve all these assets?")) return;
    try {
      setGenerating(true);
      await approveAssets(projectId);
      navigate(`/projects/${projectId}`);
    } catch (err) {
      setError("Failed to approve assets");
      setGenerating(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error && !project) return <div className="text-red-600">Error: {error}</div>;

  const validStatuses = ["VIDEO_PROMPTS_READY", "IMAGES_GENERATED", "CLIPS_GENERATED", "VOICEOVER_READY", "SUBTITLES_READY", "FINAL_RENDER_READY"];
  const isPromptsReady = validStatuses.includes(project?.status);

  const hasImages = assetPairs.length > 0 && assetPairs[0].image;
  const hasClips = assetPairs.length > 0 && assetPairs[0].clip;
  const assetsApproved = hasClips && assetPairs[0].clip.status === "APPROVED";

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Asset Generation</h2>
        <button onClick={() => navigate(`/projects/${projectId}`)} className="text-blue-600 hover:underline">
          &larr; Back to Project
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-4 rounded border border-red-200">{error}</div>}

      {/* Confirmation Modal */}
      {confirmModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4 space-y-4">
            <h3 className="text-lg font-semibold text-gray-800">Confirm Paid Generation</h3>
            <div className="space-y-2 text-sm text-gray-600">
              <div className="flex justify-between">
                <span className="text-gray-500">Provider:</span>
                <span className="font-medium">{confirmModal.estimate.provider_name}/{confirmModal.estimate.model_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Images:</span>
                <span className="font-medium">{confirmModal.estimate.estimated_jobs} image{confirmModal.estimate.estimated_jobs !== 1 ? "s" : ""}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Cost:</span>
                <span className="font-medium text-amber-600 uppercase">{confirmModal.estimate.cost_hint}</span>
              </div>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded p-3 text-sm text-amber-800">
              This will use paid provider credits. Are you sure you want to continue?
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={confirmModal.onCancel}
                className="px-4 py-2 text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={confirmModal.onConfirm}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Confirm &amp; Generate
              </button>
            </div>
          </div>
        </div>
      )}

      {!isPromptsReady && (
        <div className="bg-yellow-50 text-yellow-800 p-6 rounded-lg border border-yellow-200 shadow-sm text-center">
          <h3 className="text-lg font-medium mb-2">Prompts not approved yet</h3>
          <p>You must approve image and video prompts before generating visual assets.</p>
          <button
            onClick={() => navigate(`/projects/${projectId}/prompts`)}
            className="mt-4 px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            Go to Prompt Review
          </button>
        </div>
      )}

      {isPromptsReady && (
        <>
          <div className="flex flex-col md:flex-row justify-between items-center bg-white p-4 rounded-lg shadow-sm border border-gray-100 gap-4">
            <div>
              <span className="font-semibold text-gray-800">{assetPairs.length} Scene Assets</span>
            </div>
            <div className="space-x-3 flex flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <select
                  value={`${selectedImageProvider}:${selectedImageModel}`}
                  onChange={(e) => {
                    const [provider, model] = e.target.value.split(":");
                    setSelectedImageProvider(provider);
                    setSelectedImageModel(model);
                  }}
                  className="text-sm border border-gray-300 rounded px-2 py-1.5 bg-white"
                  disabled={generating}
                >
                  {imageModels.map(m => (
                    <option key={`${m.provider_name}:${m.model_name}`} value={`${m.provider_name}:${m.model_name}`}>
                      {m.display_name} ({m.cost_hint || "free"})
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleGenerateImages}
                  disabled={generating || assetsApproved}
                  className="px-4 py-2 bg-blue-100 text-blue-700 font-medium rounded hover:bg-blue-200 disabled:opacity-50"
                >
                  {hasImages ? "Regenerate Images" : "Generate Images"}
                </button>
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={`${selectedVideoProvider}:${selectedVideoModel}`}
                  onChange={(e) => {
                    const [provider, model] = e.target.value.split(":");
                    setSelectedVideoProvider(provider);
                    setSelectedVideoModel(model);
                  }}
                  className="text-sm border border-gray-300 rounded px-2 py-1.5 bg-white"
                  disabled={generating}
                >
                  {videoModels.map(m => (
                    <option key={`${m.provider_name}:${m.model_name}`} value={`${m.provider_name}:${m.model_name}`}>
                      {m.display_name} ({m.cost_hint || "free"})
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleGenerateClips}
                  disabled={generating || !hasImages || assetsApproved}
                  className="px-4 py-2 bg-purple-100 text-purple-700 font-medium rounded hover:bg-purple-200 disabled:opacity-50"
                >
                  {hasClips ? "Regenerate Clips" : "Generate Clips"}
                </button>
              </div>

              <button
                onClick={handleApproveAll}
                disabled={assetsApproved || generating || !hasClips}
                className="px-6 py-2 bg-green-600 text-white font-medium rounded hover:bg-green-700 disabled:opacity-50"
              >
                {assetsApproved ? "Assets Approved" : "Approve All Assets"}
              </button>
            </div>
          </div>

          {!hasImages && (
            <div className="bg-white p-12 text-center rounded-lg border border-gray-100 shadow-sm">
              <p className="text-gray-500">No assets generated yet. Click "Generate Images" to begin.</p>
            </div>
          )}

          {hasImages && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {assetPairs.map(pair => (
                <div key={pair.scene_id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden flex flex-col">
                  <div className="bg-gray-800 px-4 py-2 flex justify-between items-center">
                    <h3 className="text-white font-medium text-sm">Scene {pair.scene_number}</h3>
                  </div>

                  <div className="flex-1 flex flex-col p-4 space-y-4">

                    {/* Image Section */}
                    <div className="space-y-2 border border-gray-200 rounded p-2">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Generated Image</span>
                        {pair.image && (
                          <span className={`text-[10px] px-2 py-0.5 rounded-full ${pair.image.status === 'APPROVED' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                            {pair.image.status}
                          </span>
                        )}
                      </div>
                      {pair.image ? (
                        <>
                          <div className="aspect-[9/16] bg-gray-100 rounded overflow-hidden flex items-center justify-center">
                            {(pair.image.file_url.startsWith('data:image/svg+xml') || pair.image.file_url.startsWith('http')) ? (
                              <img src={pair.image.file_url} alt={`Scene ${pair.scene_number} Preview`} className="w-full h-full object-cover" />
                            ) : (
                              <span className="text-xs text-gray-400 break-all p-2">{pair.image.file_url}</span>
                            )}
                          </div>
                          {pair.image.provider_name && (
                            <div className="flex flex-wrap gap-1">
                              <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                                {pair.image.provider_name}/{pair.image.model_name}
                              </span>
                              {pair.image.provider_job_id && (
                                <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-400 rounded font-mono" title={pair.image.provider_job_id}>
                                  {pair.image.provider_job_id.slice(0, 12)}...
                                </span>
                              )}
                            </div>
                          )}
                          {pair.image.file_url.startsWith('http') && (
                            <a
                              href={pair.image.file_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[10px] text-blue-500 hover:underline block"
                            >
                              Open full image &nearr;
                            </a>
                          )}
                          {retryErrors[pair.scene_id] && (
                            <div className="text-[10px] text-red-500 bg-red-50 p-1 rounded">{retryErrors[pair.scene_id]}</div>
                          )}
                          {!assetsApproved && (
                            <button
                              onClick={() => handleRetryImage(pair.scene_id)}
                              disabled={generating}
                              className="w-full text-xs py-1.5 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                            >
                              Retry Image
                            </button>
                          )}
                        </>
                      ) : (
                        <div className="aspect-[9/16] bg-gray-50 border border-dashed border-gray-300 rounded flex items-center justify-center text-gray-400 text-sm">
                          No Image
                        </div>
                      )}
                    </div>

                    {/* Clip Section */}
                    <div className="space-y-2 border border-gray-200 rounded p-2">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Generated Clip</span>
                        {pair.clip && (
                          <span className={`text-[10px] px-2 py-0.5 rounded-full ${pair.clip.status === 'APPROVED' ? 'bg-green-100 text-green-700' : 'bg-purple-100 text-purple-700'}`}>
                            {pair.clip.status}
                          </span>
                        )}
                      </div>
                      {pair.clip ? (
                        <>
                          <div className="aspect-[9/16] bg-gray-100 rounded overflow-hidden flex flex-col items-center justify-center p-2 text-center break-all space-y-2">
                            <span className="text-2xl">🎬</span>
                            <span className="text-[10px] text-gray-500 font-mono">{pair.clip.file_url.split('/').pop()}</span>
                            <span className="text-[10px] text-gray-400">{pair.clip.duration_seconds}s | {pair.clip.fps}fps</span>
                          </div>
                          {pair.clip.provider_name && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              <span className="text-[10px] px-1.5 py-0.5 bg-purple-50 text-purple-600 rounded">
                                {pair.clip.provider_name}/{pair.clip.model_name}
                              </span>
                            </div>
                          )}
                          {retryErrors[pair.scene_id] && (
                            <div className="text-[10px] text-red-500 bg-red-50 p-1 rounded">{retryErrors[pair.scene_id]}</div>
                          )}
                          {!assetsApproved && (
                            <button
                              onClick={() => handleRetryClip(pair.scene_id)}
                              disabled={generating}
                              className="w-full text-xs py-1.5 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                            >
                              Retry Clip
                            </button>
                          )}
                        </>
                      ) : (
                        <div className="aspect-[9/16] bg-gray-50 border border-dashed border-gray-300 rounded flex items-center justify-center text-gray-400 text-sm">
                          No Clip
                        </div>
                      )}
                    </div>

                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AssetGeneration;
