import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getProject, updateProject, deleteProject } from "../api/projects";
import { getLatestScript } from "../api/scripts";

const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({});
  const [scriptStatus, setScriptStatus] = useState("Not generated");

  useEffect(() => {
    fetchProject();
  }, [projectId]);

  const fetchProject = async () => {
    try {
      setLoading(true);
      const data = await getProject(projectId);
      setProject(data);
      setEditData(data);
      
      try {
        const latestScript = await getLatestScript(projectId);
        setScriptStatus(latestScript.status);
      } catch (e) {
        setScriptStatus("Not generated");
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to load project");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this project?")) return;
    try {
      await deleteProject(projectId);
      navigate("/");
    } catch (err) {
      alert("Failed to delete project");
    }
  };

  const handleEditChange = (e) => {
    const { name, value } = e.target;
    setEditData((prev) => ({
      ...prev,
      [name]: name === "duration_target" ? parseInt(value) || 0 : value
    }));
  };

  const saveEdit = async () => {
    try {
      const updated = await updateProject(projectId, {
        title: editData.title,
        topic: editData.topic,
        language: editData.language,
        duration_target: editData.duration_target,
        visual_style: editData.visual_style
      });
      setProject(updated);
      setIsEditing(false);
    } catch (err) {
      alert("Failed to update project");
    }
  };

  if (loading) return <p className="text-gray-500">Loading project...</p>;
  if (error) return <div className="text-red-600">Error: {error}</div>;
  if (!project) return <p>Project not found</p>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Project Details</h2>
        <div className="space-x-3">
          {isEditing ? (
            <>
              <button onClick={() => setIsEditing(false)} className="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">Cancel</button>
              <button onClick={saveEdit} className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700">Save</button>
            </>
          ) : (
            <button onClick={() => setIsEditing(true)} className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700">Edit</button>
          )}
          <button onClick={handleDelete} className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700">Delete</button>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
        <ul className="space-y-4">
          <li className="flex flex-col border-b pb-2">
            <span className="font-medium text-gray-600 text-sm">Title</span>
            {isEditing ? (
              <input type="text" name="title" value={editData.title} onChange={handleEditChange} className="border p-1 mt-1 rounded w-full" />
            ) : (
              <span className="text-gray-900 text-lg">{project.title}</span>
            )}
          </li>
          
          <li className="flex flex-col border-b pb-2">
            <span className="font-medium text-gray-600 text-sm">Topic</span>
            {isEditing ? (
              <textarea name="topic" value={editData.topic} onChange={handleEditChange} className="border p-1 mt-1 rounded w-full" rows="2" />
            ) : (
              <span className="text-gray-900">{project.topic}</span>
            )}
          </li>
          
          <li className="flex flex-col border-b pb-2">
            <span className="font-medium text-gray-600 text-sm">Status</span>
            <span className="text-blue-600 font-semibold uppercase">{project.status}</span>
          </li>
          
          <div className="grid grid-cols-2 gap-4 border-b pb-2">
            <li className="flex flex-col">
              <span className="font-medium text-gray-600 text-sm">Language</span>
              {isEditing ? (
                <select name="language" value={editData.language} onChange={handleEditChange} className="border p-1 mt-1 rounded">
                  <option value="en">English</option>
                  <option value="ms">Bahasa Melayu</option>
                </select>
              ) : (
                <span className="text-gray-900">{project.language}</span>
              )}
            </li>
            <li className="flex flex-col">
              <span className="font-medium text-gray-600 text-sm">Duration Target</span>
              {isEditing ? (
                <input type="number" name="duration_target" value={editData.duration_target} onChange={handleEditChange} className="border p-1 mt-1 rounded w-24" />
              ) : (
                <span className="text-gray-900">{project.duration_target}s</span>
              )}
            </li>
          </div>
          
          <div className="grid grid-cols-2 gap-4 border-b pb-2">
            <li className="flex flex-col">
              <span className="font-medium text-gray-600 text-sm">Aspect Ratio</span>
              <span className="text-gray-900">{project.aspect_ratio}</span>
            </li>
            <li className="flex flex-col">
              <span className="font-medium text-gray-600 text-sm">Visual Style</span>
              {isEditing ? (
                <input type="text" name="visual_style" value={editData.visual_style} onChange={handleEditChange} className="border p-1 mt-1 rounded w-full" />
              ) : (
                <span className="text-gray-900">{project.visual_style}</span>
              )}
            </li>
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-xs text-gray-500 pt-2">
            <li>Created: {new Date(project.created_at).toLocaleString()}</li>
            <li>Updated: {new Date(project.updated_at).toLocaleString()}</li>
          </div>
        </ul>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Script</h3>
          <p className="text-sm text-gray-500 mt-1">Status: <span className="font-medium text-gray-700">{scriptStatus}</span></p>
        </div>
        <Link 
          to={`/projects/${projectId}/script`} 
          className="px-4 py-2 bg-blue-600 text-white font-medium rounded hover:bg-blue-700"
        >
          {scriptStatus === "Not generated" ? "Generate Script" : "View/Edit Script"}
        </Link>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Scene Plan</h3>
          <p className="text-sm text-gray-500 mt-1">
            {["DRAFT_CREATED", "TOPIC_ANALYZED", "RESEARCH_NOTES_READY"].includes(project.status) 
              ? "Approve a script first"
              : project.status === "SCRIPT_READY" 
                ? "Ready to plan"
                : "Plan approved"}
          </p>
        </div>
        <Link 
          to={`/projects/${projectId}/scenes`} 
          className={`px-4 py-2 font-medium rounded ${
            ["DRAFT_CREATED", "TOPIC_ANALYZED", "RESEARCH_NOTES_READY"].includes(project.status)
              ? "bg-gray-200 text-gray-400 cursor-not-allowed pointer-events-none"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          Open Scene Planner
        </Link>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Prompts</h3>
          <p className="text-sm text-gray-500 mt-1">
            {["DRAFT_CREATED", "TOPIC_ANALYZED", "RESEARCH_NOTES_READY", "SCRIPT_READY"].includes(project.status) 
              ? "Approve scene plan first"
              : project.status === "SCENE_PLAN_READY" 
                ? "Ready to generate"
                : "Prompts approved"}
          </p>
        </div>
        <Link 
          to={`/projects/${projectId}/prompts`} 
          className={`px-4 py-2 font-medium rounded ${
            ["DRAFT_CREATED", "TOPIC_ANALYZED", "RESEARCH_NOTES_READY", "SCRIPT_READY"].includes(project.status)
              ? "bg-gray-200 text-gray-400 cursor-not-allowed pointer-events-none"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          Review Prompts
        </Link>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Assets</h3>
          <p className="text-sm text-gray-500 mt-1">
            {["DRAFT_CREATED", "TOPIC_ANALYZED", "RESEARCH_NOTES_READY", "SCRIPT_READY", "SCENE_PLAN_READY"].includes(project.status) 
              ? "Approve prompts first"
              : ["VIDEO_PROMPTS_READY", "IMAGES_GENERATED"].includes(project.status) 
                ? "Ready to generate"
                : "Assets approved"}
          </p>
        </div>
        <Link 
          to={`/projects/${projectId}/assets`} 
          className={`px-4 py-2 font-medium rounded ${
            ["DRAFT_CREATED", "TOPIC_ANALYZED", "RESEARCH_NOTES_READY", "SCRIPT_READY", "SCENE_PLAN_READY"].includes(project.status)
              ? "bg-gray-200 text-gray-400 cursor-not-allowed pointer-events-none"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          Generate Assets
        </Link>
      </div>
    </div>
  );
};

export default ProjectDetail;
