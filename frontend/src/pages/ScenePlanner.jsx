import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getProject } from "../api/projects";
import { listProjectScenes, generateScenes, updateScene, approveScenePlan } from "../api/scenes";
import { listEnabledProviderModels } from "../api/providers";

const ScenePlanner = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  
  const [project, setProject] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState(null);
  
  const [llmModels, setLlmModels] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState("mock");
  const [selectedModel, setSelectedModel] = useState("mock-llm");
  
  // Track edits per scene using a dictionary keyed by scene.id
  const [editData, setEditData] = useState({});

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const proj = await getProject(projectId);
      setProject(proj);
      
      const loadedScenes = await listProjectScenes(projectId);
      setScenes(loadedScenes);
      
      const edits = {};
      loadedScenes.forEach(s => { edits[s.id] = { ...s }; });
      setEditData(edits);
      
      try {
        const models = await listEnabledProviderModels();
        const llms = models.filter(m => m.modality === 'llm');
        setLlmModels(llms);
        if (llms.length > 0) {
            const mock = llms.find(m => m.provider_name === 'mock' && m.model_name === 'mock-llm');
            if (mock) {
                setSelectedProvider(mock.provider_name);
                setSelectedModel(mock.model_name);
            } else {
                setSelectedProvider(llms[0].provider_name);
                setSelectedModel(llms[0].model_name);
            }
        }
      } catch (err) {
        console.error("Failed to load models", err);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load scene planner data");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      const newScenes = await generateScenes(projectId, {
        provider_name: selectedProvider,
        model_name: selectedModel
      });
      setScenes(newScenes);
      
      const edits = {};
      newScenes.forEach(s => { edits[s.id] = { ...s }; });
      setEditData(edits);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate scenes");
    } finally {
      setGenerating(false);
    }
  };

  const handleEditChange = (sceneId, e) => {
    const { name, value } = e.target;
    setEditData(prev => ({
      ...prev,
      [sceneId]: {
        ...prev[sceneId],
        [name]: name === "duration_seconds" ? parseInt(value) || 0 : value
      }
    }));
  };

  const handleSaveScene = async (sceneId) => {
    try {
      setSavingId(sceneId);
      const dataToSave = editData[sceneId];
      const updated = await updateScene(sceneId, {
        duration_seconds: dataToSave.duration_seconds,
        narration_text: dataToSave.narration_text,
        visual_summary: dataToSave.visual_summary,
        camera_direction: dataToSave.camera_direction,
        motion_direction: dataToSave.motion_direction,
        sfx_notes: dataToSave.sfx_notes
      });
      
      setScenes(prev => prev.map(s => s.id === sceneId ? updated : s));
      setEditData(prev => ({ ...prev, [sceneId]: updated }));
    } catch (err) {
      alert("Failed to save scene");
    } finally {
      setSavingId(null);
    }
  };

  const handleApprovePlan = async () => {
    if (!window.confirm("Are you sure you want to approve this entire scene plan?")) return;
    try {
      setGenerating(true); // Reusing this for loading state
      await approveScenePlan(projectId);
      navigate(`/projects/${projectId}`);
    } catch (err) {
      alert("Failed to approve scene plan");
      setGenerating(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error && !project) return <div className="text-red-600">Error: {error}</div>;

  const isScriptReady = ["SCRIPT_READY", "SCENE_PLAN_READY", "IMAGE_PROMPTS_READY", "VIDEO_PROMPTS_READY", "IMAGES_GENERATED", "CLIPS_GENERATED", "VOICEOVER_READY", "SUBTITLES_READY", "FINAL_RENDER_READY"].includes(project?.status);
  const planApproved = scenes.length > 0 && scenes[0].status === "APPROVED";

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Scene Planner</h2>
        <button onClick={() => navigate(`/projects/${projectId}`)} className="text-blue-600 hover:underline">
          &larr; Back to Project
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-4 rounded border border-red-200">{error}</div>}

      {!isScriptReady && (
        <div className="bg-yellow-50 text-yellow-800 p-6 rounded-lg border border-yellow-200 shadow-sm text-center">
          <h3 className="text-lg font-medium mb-2">Script not approved yet</h3>
          <p>You must approve a script before you can plan the scenes.</p>
          <button 
            onClick={() => navigate(`/projects/${projectId}/script`)}
            className="mt-4 px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            Go to Script Review
          </button>
        </div>
      )}

      {isScriptReady && scenes.length === 0 && (
        <div className="bg-white p-12 text-center rounded-lg border border-gray-100 shadow-sm">
          <h3 className="text-xl font-medium text-gray-700 mb-2">No scenes generated</h3>
          <p className="text-gray-500 mb-6">Let the AI generate a starting scene plan based on your approved script.</p>
          <div className="flex flex-col items-center gap-4">
            <div className="flex flex-col items-start gap-1">
              <label className="text-sm text-gray-600 font-medium">LLM Provider</label>
              <select
                value={`${selectedProvider}|${selectedModel}`}
                onChange={(e) => {
                  const [p, m] = e.target.value.split('|');
                  setSelectedProvider(p);
                  setSelectedModel(m);
                }}
                className="border border-gray-300 rounded p-2 text-sm min-w-[200px]"
              >
                {llmModels.map(m => (
                  <option key={`${m.provider_name}|${m.model_name}`} value={`${m.provider_name}|${m.model_name}`}>
                    {m.display_name} ({m.provider_name})
                  </option>
                ))}
              </select>
            </div>
            <button 
              onClick={handleGenerate} 
              disabled={generating}
              className="px-6 py-3 bg-blue-600 text-white font-medium rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {generating ? "Generating..." : "Generate Scene Plan"}
            </button>
          </div>
        </div>
      )}

      {scenes.length > 0 && (
        <>
          <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border border-gray-100">
            <div>
              <span className="font-semibold text-gray-800">{scenes.length} Scenes</span>
              <span className="text-gray-500 ml-4">Total Duration: {scenes.reduce((acc, s) => acc + s.duration_seconds, 0)}s</span>
            </div>
            <div className="space-x-4 flex items-center">
              <select
                value={`${selectedProvider}|${selectedModel}`}
                onChange={(e) => {
                  const [p, m] = e.target.value.split('|');
                  setSelectedProvider(p);
                  setSelectedModel(m);
                }}
                disabled={generating || planApproved}
                className="border border-gray-300 rounded p-2 text-sm max-w-[200px]"
              >
                {llmModels.map(m => (
                  <option key={`${m.provider_name}|${m.model_name}`} value={`${m.provider_name}|${m.model_name}`}>
                    {m.display_name}
                  </option>
                ))}
              </select>
              <button 
                onClick={handleGenerate} 
                disabled={generating || planApproved}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
              >
                {generating ? "Regenerating..." : "Regenerate All"}
              </button>
              <button 
                onClick={handleApprovePlan} 
                disabled={planApproved || generating}
                className="px-6 py-2 bg-green-600 text-white font-medium rounded hover:bg-green-700 disabled:opacity-50"
              >
                {planApproved ? "Plan Approved" : "Approve Plan"}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {scenes.map(scene => {
              const data = editData[scene.id] || scene;
              return (
                <div key={scene.id} className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col">
                  <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex justify-between items-center">
                    <h4 className="font-semibold text-gray-700">Scene {scene.scene_number}</h4>
                    <span className={`text-xs px-2 py-1 rounded-full ${scene.status === 'APPROVED' ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-600'}`}>
                      {scene.status}
                    </span>
                  </div>
                  
                  <div className="p-4 space-y-3 flex-1">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Narration Text</label>
                      <textarea 
                        name="narration_text"
                        value={data.narration_text}
                        onChange={(e) => handleEditChange(scene.id, e)}
                        disabled={planApproved}
                        className="w-full text-sm p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 min-h-[60px]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Visual Summary</label>
                      <textarea 
                        name="visual_summary"
                        value={data.visual_summary}
                        onChange={(e) => handleEditChange(scene.id, e)}
                        disabled={planApproved}
                        className="w-full text-sm p-2 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 min-h-[60px]"
                      />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Camera</label>
                        <input 
                          type="text"
                          name="camera_direction"
                          value={data.camera_direction || ""}
                          onChange={(e) => handleEditChange(scene.id, e)}
                          disabled={planApproved}
                          className="w-full text-sm p-1.5 border border-gray-300 rounded"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Motion</label>
                        <input 
                          type="text"
                          name="motion_direction"
                          value={data.motion_direction || ""}
                          onChange={(e) => handleEditChange(scene.id, e)}
                          disabled={planApproved}
                          className="w-full text-sm p-1.5 border border-gray-300 rounded"
                        />
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                       <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">SFX Notes</label>
                        <input 
                          type="text"
                          name="sfx_notes"
                          value={data.sfx_notes || ""}
                          onChange={(e) => handleEditChange(scene.id, e)}
                          disabled={planApproved}
                          className="w-full text-sm p-1.5 border border-gray-300 rounded"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Duration (s)</label>
                        <input 
                          type="number"
                          name="duration_seconds"
                          value={data.duration_seconds}
                          onChange={(e) => handleEditChange(scene.id, e)}
                          disabled={planApproved}
                          className="w-full text-sm p-1.5 border border-gray-300 rounded"
                        />
                      </div>
                    </div>
                  </div>
                  
                  {!planApproved && (
                    <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 flex justify-end">
                      <button 
                        onClick={() => handleSaveScene(scene.id)}
                        disabled={savingId === scene.id}
                        className="px-4 py-1.5 text-sm bg-blue-100 text-blue-700 font-medium rounded hover:bg-blue-200 disabled:opacity-50"
                      >
                        {savingId === scene.id ? "Saving..." : "Save Scene"}
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

export default ScenePlanner;
