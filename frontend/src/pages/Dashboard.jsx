import React, { useEffect, useState } from "react";
import apiClient from "../api/client";

const Dashboard = () => {
  const [healthData, setHealthData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await apiClient.get("/api/health");
        setHealthData(response.data);
      } catch (err) {
        setError(err.message || "Failed to fetch health check");
      } finally {
        setLoading(false);
      }
    };
    
    fetchHealth();
  }, []);

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Dashboard</h2>
      
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold mb-4 text-gray-700">System Status</h3>
        
        {loading && <p className="text-gray-500">Checking system health...</p>}
        
        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded border border-red-200">
            <strong>Error: </strong> {error}
          </div>
        )}
        
        {healthData && (
          <ul className="space-y-3">
            <li className="flex justify-between border-b pb-2">
              <span className="font-medium text-gray-600">App Name</span>
              <span className="text-gray-900">{healthData.app_name}</span>
            </li>
            <li className="flex justify-between border-b pb-2">
              <span className="font-medium text-gray-600">Environment</span>
              <span className="text-gray-900 capitalize">{healthData.environment}</span>
            </li>
            <li className="flex justify-between border-b pb-2">
              <span className="font-medium text-gray-600">API Status</span>
              <span className="text-green-600 font-semibold uppercase">{healthData.status}</span>
            </li>
            <li className="flex justify-between">
              <span className="font-medium text-gray-600">Storage Initialized</span>
              <span className={healthData.storage_path_exists ? "text-green-600" : "text-red-600"}>
                {healthData.storage_path_exists ? "Yes" : "No"}
              </span>
            </li>
          </ul>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
