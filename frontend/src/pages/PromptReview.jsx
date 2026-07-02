import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getProject } from "../api/projects";
import { listProjectPrompts, generatePrompts, updateImagePrompt, updateVideoPrompt, approvePrompts } from "../api/prompts";

const PromptReview = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  
  const [project, setProject] = useState(null);
  const [promptPairs, setPromptPairs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState(null);
  
  // Track edits per scene using a dictionary keyed by scene_id
  const [editData, setEditData] = useState({});

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const proj = await getProject(projectId);
      setProject(proj);
      
      const loadedPairs = await listProjectPrompts(projectId);
      setPromptPairs(loadedPairs);
      
      initializeEdits(loadedPairs);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load prompt review data");
    } finally {
      setLoading(false);
    }
  };
  
  const initializeEdits = (pairs) => {
    const edits = {};
    pairs.forEach(p => {
      edits[p.scene_id] = { 
        image: p.image_prompt ? { ...p.image_prompt } : {},
        video: p.video_prompt ? { ...p.video_prompt } : {}
      };
    });
    setEditData(edits);
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      const newPairs = await generatePrompts(projectId);
      setPromptPairs(newPairs);
      initializeEdits(newPairs);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate prompts");
    } finally {
      setGenerating(false);
    }
  };

  const handleImageEdit = (sceneId, e) => {
    const { name, value } = e.target;
    setEditData(prev => ({
      ...prev,
      [sceneId]: {
        ...prev[sceneId],
        image: { ...prev[sceneId].image, [name]: value }
      }
    }));
  };

  const handleVideoEdit = (sceneId, e) => {
    const { name, value } = e.target;
    setEditData(prev => ({
      ...prev,
      [sceneId]: {
        ...prev[sceneId],
        video: { ...prev[sceneId].video, [name]: name === "duration_seconds" ? parseInt(value) || 0 : value }
      }
    }));
  };

  const handleSaveScenePrompts = async (sceneId, imgId, vidId) => {
    try {
      setSavingId(sceneId);
      const dataToSave = editData[sceneId];
      
      let updatedImg = null;
      let updatedVid = null;
      
      if (imgId) {
        updatedImg = await updateImagePrompt(imgId, {
          prompt_text: dataToSave.image.prompt_text,
          negative_prompt: dataToSave.image.negative_prompt,
          style_lock: dataToSave.image.style_lock,
          provider: dataToSave.image.provider,
          model: dataToSave.image.model
        });
      }
      
      if (vidId) {
        updatedVid = await updateVideoPrompt(vidId, {
          prompt_text: dataToSave.video.prompt_text,
          negative_prompt: dataToSave.video.negative_prompt,
          duration_seconds: dataToSave.video.duration_seconds,
          motion_strength: dataToSave.video.motion_strength,
          camera_lock: dataToSave.video.camera_lock,
          provider: dataToSave.video.provider,
          model: dataToSave.video.model
        });
      }
      
      setPromptPairs(prev => prev.map(p => {
        if (p.scene_id === sceneId) {
          return {
            ...p,
            image_prompt: updatedImg || p.image_prompt,
            video_prompt: updatedVid || p.video_prompt
          };
        }
        return p;
      }));
      
    } catch (err) {
      alert("Failed to save prompts");
    } finally {
      setSavingId(null);
    }
  };

  const handleApproveAll = async () => {
    if (!window.confirm("Are you sure you want to approve all image and video prompts?")) return;
    try {
      setGenerating(true);
      await approvePrompts(projectId);
      navigate(`/projects/${projectId}`);
    } catch (err) {
      alert("Failed to approve prompts");
      setGenerating(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error && !project) return <div className="text-red-600">Error: {error}</div>;

  const validStatuses = ["SCENE_PLAN_READY", "IMAGE_PROMPTS_READY", "VIDEO_PROMPTS_READY", "IMAGES_GENERATED", "CLIPS_GENERATED", "VOICEOVER_READY", "SUBTITLES_READY", "FINAL_RENDER_READY"];
  const isScenePlanReady = validStatuses.includes(project?.status);
  
  // Check if we have valid prompts
  const hasPrompts = promptPairs.length > 0 && promptPairs[0].image_prompt;
  const planApproved = hasPrompts && promptPairs[0].image_prompt.status === "APPROVED";

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Prompt Review</h2>
        <button onClick={() => navigate(`/projects/${projectId}`)} className="text-blue-600 hover:underline">
          &larr; Back to Project
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-4 rounded border border-red-200">{error}</div>}

      {!isScenePlanReady && (
        <div className="bg-yellow-50 text-yellow-800 p-6 rounded-lg border border-yellow-200 shadow-sm text-center">
          <h3 className="text-lg font-medium mb-2">Scene plan not approved yet</h3>
          <p>You must approve a scene plan before generating prompts.</p>
          <button 
            onClick={() => navigate(`/projects/${projectId}/scenes`)}
            className="mt-4 px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            Go to Scene Planner
          </button>
        </div>
      )}

      {isScenePlanReady && !hasPrompts && (
        <div className="bg-white p-12 text-center rounded-lg border border-gray-100 shadow-sm">
          <h3 className="text-xl font-medium text-gray-700 mb-2">No prompts generated</h3>
          <p className="text-gray-500 mb-6">Generate image and video prompts based on your approved scene plan.</p>
          <button 
            onClick={handleGenerate} 
            disabled={generating}
            className="px-6 py-3 bg-blue-600 text-white font-medium rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {generating ? "Generating..." : "Generate Prompts"}
          </button>
        </div>
      )}

      {hasPrompts && (
        <>
          <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border border-gray-100">
            <div>
              <span className="font-semibold text-gray-800">{promptPairs.length} Scene Prompts</span>
            </div>
            <div className="space-x-4">
              <button 
                onClick={handleGenerate} 
                disabled={generating || planApproved}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
              >
                {generating ? "Regenerating..." : "Regenerate All"}
              </button>
              <button 
                onClick={handleApproveAll} 
                disabled={planApproved || generating}
                className="px-6 py-2 bg-green-600 text-white font-medium rounded hover:bg-green-700 disabled:opacity-50"
              >
                {planApproved ? "Prompts Approved" : "Approve All Prompts"}
              </button>
            </div>
          </div>

          <div className="space-y-8">
            {promptPairs.map(pair => {
              const imgData = editData[pair.scene_id]?.image || pair.image_prompt;
              const vidData = editData[pair.scene_id]?.video || pair.video_prompt;
              
              return (
                <div key={pair.scene_id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                  <div className="bg-gray-800 px-6 py-3 flex justify-between items-center">
                    <h3 className="text-white font-medium">Scene {pair.scene_number}</h3>
                    <span className={`text-xs px-2 py-1 rounded ${planApproved ? 'bg-green-500 text-white' : 'bg-gray-600 text-gray-300'}`}>
                      {planApproved ? 'APPROVED' : 'DRAFT'}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-gray-200">
                    {/* Image Prompt Column */}
                    <div className="p-6 space-y-4">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="font-semibold text-gray-700 flex items-center">
                          <span className="bg-blue-100 text-blue-700 p-1 rounded mr-2">📷</span> Image Prompt
                        </h4>
                      </div>
                      
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Prompt Text</label>
                        <textarea 
                          name="prompt_text"
                          value={imgData.prompt_text}
                          onChange={(e) => handleImageEdit(pair.scene_id, e)}
                          disabled={planApproved}
                          className="w-full text-sm p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 min-h-[120px]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Negative Prompt</label>
                        <textarea 
                          name="negative_prompt"
                          value={imgData.negative_prompt || ""}
                          onChange={(e) => handleImageEdit(pair.scene_id, e)}
                          disabled={planApproved}
                          className="w-full text-sm p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 min-h-[60px]"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">Style Lock</label>
                          <input 
                            type="text" name="style_lock" value={imgData.style_lock || ""} onChange={(e) => handleImageEdit(pair.scene_id, e)}
                            disabled={planApproved} className="w-full text-sm p-1.5 border border-gray-300 rounded"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">Provider/Model</label>
                          <div className="flex space-x-1">
                            <input type="text" name="provider" value={imgData.provider} onChange={(e) => handleImageEdit(pair.scene_id, e)} disabled={planApproved} className="w-1/2 text-xs p-1.5 border border-gray-300 rounded" />
                            <input type="text" name="model" value={imgData.model} onChange={(e) => handleImageEdit(pair.scene_id, e)} disabled={planApproved} className="w-1/2 text-xs p-1.5 border border-gray-300 rounded" />
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Video Prompt Column */}
                    <div className="p-6 space-y-4">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="font-semibold text-gray-700 flex items-center">
                          <span className="bg-purple-100 text-purple-700 p-1 rounded mr-2">🎬</span> Video Prompt
                        </h4>
                      </div>
                      
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Prompt Text</label>
                        <textarea 
                          name="prompt_text"
                          value={vidData.prompt_text}
                          onChange={(e) => handleVideoEdit(pair.scene_id, e)}
                          disabled={planApproved}
                          className="w-full text-sm p-2 border border-gray-300 rounded focus:ring-1 focus:ring-purple-500 min-h-[120px]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Negative Prompt</label>
                        <textarea 
                          name="negative_prompt"
                          value={vidData.negative_prompt || ""}
                          onChange={(e) => handleVideoEdit(pair.scene_id, e)}
                          disabled={planApproved}
                          className="w-full text-sm p-2 border border-gray-300 rounded focus:ring-1 focus:ring-purple-500 min-h-[60px]"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                           <label className="block text-xs font-medium text-gray-500 mb-1">Motion Strength</label>
                           <input type="text" name="motion_strength" value={vidData.motion_strength || ""} onChange={(e) => handleVideoEdit(pair.scene_id, e)} disabled={planApproved} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">Camera Lock</label>
                          <input type="text" name="camera_lock" value={vidData.camera_lock || ""} onChange={(e) => handleVideoEdit(pair.scene_id, e)} disabled={planApproved} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                         <div>
                           <label className="block text-xs font-medium text-gray-500 mb-1">Duration (s)</label>
                           <input type="number" name="duration_seconds" value={vidData.duration_seconds} onChange={(e) => handleVideoEdit(pair.scene_id, e)} disabled={planApproved} className="w-full text-sm p-1.5 border border-gray-300 rounded" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">Provider/Model</label>
                          <div className="flex space-x-1">
                            <input type="text" name="provider" value={vidData.provider} onChange={(e) => handleVideoEdit(pair.scene_id, e)} disabled={planApproved} className="w-1/2 text-xs p-1.5 border border-gray-300 rounded" />
                            <input type="text" name="model" value={vidData.model} onChange={(e) => handleVideoEdit(pair.scene_id, e)} disabled={planApproved} className="w-1/2 text-xs p-1.5 border border-gray-300 rounded" />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {!planApproved && (
                    <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 flex justify-end">
                      <button 
                        onClick={() => handleSaveScenePrompts(pair.scene_id, pair.image_prompt?.id, pair.video_prompt?.id)}
                        disabled={savingId === pair.scene_id}
                        className="px-6 py-2 text-sm bg-blue-100 text-blue-700 font-medium rounded hover:bg-blue-200 disabled:opacity-50"
                      >
                        {savingId === pair.scene_id ? "Saving..." : "Save Pair"}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default PromptReview;
