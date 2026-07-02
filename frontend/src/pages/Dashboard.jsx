import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import apiClient from "../api/client";
import { listProjects } from "../api/projects";

const Dashboard = () => {
  const [healthData, setHealthData] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const healthRes = await apiClient.get("/api/health");
        setHealthData(healthRes.data);
        
        const projRes = await listProjects();
        setProjects(projRes);
      } catch (err) {
        console.error("Dashboard error:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchDashboardData();
  }, []);

  return (
    <div className="max-w-6xl mx-auto flex flex-col md:flex-row gap-6">
      <div className="w-full md:w-3/4 order-2 md:order-1">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">Projects</h2>
          <Link 
            to="/projects/new" 
            className="px-4 py-2 bg-blue-600 text-white font-medium rounded hover:bg-blue-700 transition"
          >
            Create Project
          </Link>
        </div>
        
        {loading ? (
          <p className="text-gray-500">Loading projects...</p>
        ) : projects.length === 0 ? (
          <div className="bg-white p-8 text-center rounded-lg border border-gray-100 shadow-sm">
            <h3 className="text-lg font-medium text-gray-700 mb-2">No projects yet</h3>
            <p className="text-gray-500 mb-4">Get started by creating your first explainer short project.</p>
            <Link to="/projects/new" className="text-blue-600 font-medium hover:underline">Create one now &rarr;</Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projects.map((proj) => (
              <Link key={proj.id} to={`/projects/${proj.id}`} className="block bg-white p-5 rounded-lg border border-gray-100 shadow-sm hover:shadow-md transition">
                <h3 className="text-lg font-semibold text-gray-800 mb-1 truncate">{proj.title}</h3>
                <p className="text-sm text-gray-500 mb-3 truncate">{proj.topic}</p>
                <div className="flex justify-between items-center text-xs">
                  <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full font-medium">{proj.status}</span>
                  <span className="text-gray-400">{new Date(proj.updated_at).toLocaleDateString()}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="w-full md:w-1/4 order-1 md:order-2">
        <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-100 sticky top-6">
          <h3 className="text-sm font-semibold mb-3 text-gray-700 uppercase tracking-wider">System Status</h3>
          {healthData ? (
            <ul className="space-y-2 text-sm">
              <li className="flex justify-between border-b pb-1">
                <span className="text-gray-500">API</span>
                <span className="text-green-600 font-medium">{healthData.status}</span>
              </li>
              <li className="flex justify-between border-b pb-1">
                <span className="text-gray-500">Env</span>
                <span className="text-gray-800 capitalize">{healthData.environment}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-gray-500">Storage</span>
                <span className={healthData.storage_path_exists ? "text-green-600" : "text-red-600"}>
                  {healthData.storage_path_exists ? "OK" : "Error"}
                </span>
              </li>
            </ul>
          ) : (
            <p className="text-xs text-gray-400">Loading system status...</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
