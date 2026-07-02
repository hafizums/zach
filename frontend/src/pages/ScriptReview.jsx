import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getProject } from "../api/projects";
import { getLatestScript, generateScript, updateScript, approveScript } from "../api/scripts";
import { listEnabledProviderModels } from "../api/providers";

const ScriptReview = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  
  const [project, setProject] = useState(null);
  const [script, setScript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  
  const [llmModels, setLlmModels] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState("mock");
  const [selectedModel, setSelectedModel] = useState("mock-llm");
  
  const [editData, setEditData] = useState(null);

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const proj = await getProject(projectId);
      setProject(proj);
      
      try {
        const latest = await getLatestScript(projectId);
        setScript(latest);
        setEditData(latest);
      } catch (e) {
        // 404 means no script yet
        setScript(null);
      }
      try {
        const models = await listEnabledProviderModels();
        const llms = models.filter(m => m.modality === 'llm');
        setLlmModels(llms);
        if (llms.length > 0) {
            // Check if mock is available to set as default, else first
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
      setError(err.response?.data?.detail || "Failed to load project data");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      const newScript = await generateScript(projectId, { 
        provider_name: selectedProvider, 
        model_name: selectedModel 
      });
      setScript(newScript);
      setEditData(newScript);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate script");
    } finally {
      setGenerating(false);
    }
  };

  const handleEditChange = (e) => {
    const { name, value } = e.target;
    setEditData(prev => ({
      ...prev,
      [name]: name === "estimated_duration" ? parseInt(value) || 0 : value
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const updated = await updateScript(script.id, {
        script_text: editData.script_text,
        hook: editData.hook,
        payoff: editData.payoff,
        estimated_duration: editData.estimated_duration
      });
      setScript(updated);
      setEditData(updated);
      alert("Script saved successfully!");
    } catch (err) {
      alert("Failed to save script edits");
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!window.confirm("Are you sure you want to approve this script?")) return;
    try {
      setSaving(true);
      await approveScript(script.id);
      navigate(`/projects/${projectId}`);
    } catch (err) {
      alert("Failed to approve script");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error && !project) return <div className="text-red-600">Error: {error}</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Script Review</h2>
        <button onClick={() => navigate(`/projects/${projectId}`)} className="text-blue-600 hover:underline">
          &larr; Back to Project
        </button>
      </div>

      <div className="bg-white p-4 rounded border border-gray-100 shadow-sm mb-6 flex justify-between">
        <div>
          <span className="text-gray-500 text-sm block">Project</span>
          <span className="font-semibold text-gray-800">{project.title}</span>
        </div>
        <div className="text-right">
          <span className="text-gray-500 text-sm block">Target</span>
          <span className="font-semibold text-gray-800">{project.duration_target}s</span>
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-4 rounded border border-red-200">{error}</div>}

      {!script ? (
        <div className="bg-white p-12 text-center rounded-lg border border-gray-100 shadow-sm">
          <h3 className="text-xl font-medium text-gray-700 mb-2">No script found</h3>
          <p className="text-gray-500 mb-6">Generate the first script for this project.</p>
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
              {generating ? "Generating..." : "Generate Script"}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-semibold">Version {script.version}</span>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${script.status === 'APPROVED' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                {script.status}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={`${selectedProvider}|${selectedModel}`}
                onChange={(e) => {
                  const [p, m] = e.target.value.split('|');
                  setSelectedProvider(p);
                  setSelectedModel(m);
                }}
                disabled={generating || script.status === 'APPROVED'}
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
                disabled={generating || script.status === 'APPROVED'}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50"
              >
                {generating ? "Regenerating..." : "Regenerate New Version"}
              </button>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hook</label>
              <input 
                type="text" 
                name="hook" 
                value={editData.hook || ""} 
                onChange={handleEditChange}
                disabled={script.status === 'APPROVED'}
                className="w-full p-2 border border-gray-300 rounded focus:ring focus:ring-blue-200 disabled:bg-gray-50"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Script Text</label>
              <textarea 
                name="script_text" 
                value={editData.script_text} 
                onChange={handleEditChange}
                disabled={script.status === 'APPROVED'}
                rows="6"
                className="w-full p-2 border border-gray-300 rounded focus:ring focus:ring-blue-200 disabled:bg-gray-50"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Payoff</label>
              <input 
                type="text" 
                name="payoff" 
                value={editData.payoff || ""} 
                onChange={handleEditChange}
                disabled={script.status === 'APPROVED'}
                className="w-full p-2 border border-gray-300 rounded focus:ring focus:ring-blue-200 disabled:bg-gray-50"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
               <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Estimated Duration (s)</label>
                <input 
                  type="number" 
                  name="estimated_duration" 
                  value={editData.estimated_duration} 
                  onChange={handleEditChange}
                  disabled={script.status === 'APPROVED'}
                  className="w-full p-2 border border-gray-300 rounded focus:ring focus:ring-blue-200 disabled:bg-gray-50"
                />
              </div>
               <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Word Count</label>
                <input 
                  type="number" 
                  disabled 
                  value={script.word_count} 
                  className="w-full p-2 border border-gray-300 rounded bg-gray-50 text-gray-500"
                />
              </div>
            </div>
          </div>

          {script.status !== 'APPROVED' && (
            <div className="flex justify-end space-x-4">
              <button 
                onClick={handleSave} 
                disabled={saving}
                className="px-6 py-2 bg-blue-100 text-blue-700 font-medium rounded hover:bg-blue-200 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Edits"}
              </button>
              <button 
                onClick={handleApprove} 
                disabled={saving}
                className="px-6 py-2 bg-green-600 text-white font-medium rounded hover:bg-green-700 disabled:opacity-50"
              >
                Approve Script
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ScriptReview;
