import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject } from "../api/projects";

const CreateProject = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    title: "",
    topic: "",
    language: "en",
    duration_target: 30,
    visual_style: "semi_realistic_3d_explainer"
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "duration_target" ? parseInt(value) || 0 : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const project = await createProject(formData);
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Create New Project</h2>
      
      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded mb-6 border border-red-200">
          <strong>Error: </strong> {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <input 
            type="text" 
            name="title" 
            required 
            value={formData.title} 
            onChange={handleChange}
            className="w-full p-2 border border-gray-300 rounded focus:ring focus:ring-blue-200"
            placeholder="e.g. King Cobra Bite Explainer"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Topic</label>
          <textarea 
            name="topic" 
            required 
            value={formData.topic} 
            onChange={handleChange}
            className="w-full p-2 border border-gray-300 rounded focus:ring focus:ring-blue-200"
            placeholder="e.g. How a king cobra bite shuts down the body"
            rows="3"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
          <select 
            name="language" 
            value={formData.language} 
            onChange={handleChange}
            className="w-full p-2 border border-gray-300 rounded focus:ring focus:ring-blue-200"
          >
            <option value="en">English</option>
            <option value="ms">Bahasa Melayu</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Duration (seconds)</label>
          <input 
            type="number" 
            name="duration_target" 
            required 
            min="10"
            max="60"
            value={formData.duration_target} 
            onChange={handleChange}
            className="w-full p-2 border border-gray-300 rounded focus:ring focus:ring-blue-200"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Visual Style</label>
          <input 
            type="text" 
            name="visual_style" 
            required 
            value={formData.visual_style} 
            onChange={handleChange}
            className="w-full p-2 border border-gray-300 rounded focus:ring focus:ring-blue-200"
          />
        </div>

        <div className="pt-4 flex items-center space-x-4">
          <button 
            type="button" 
            onClick={() => navigate("/")}
            className="px-4 py-2 text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
          >
            Cancel
          </button>
          <button 
            type="submit" 
            disabled={loading}
            className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Creating..." : "Create Project"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateProject;
