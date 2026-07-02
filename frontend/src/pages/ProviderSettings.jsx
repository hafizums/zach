import React, { useState, useEffect } from 'react';
import { 
    listProviderModels, 
    enableProviderModel, 
    disableProviderModel, 
    listRecentProviderRuns, 
    preflightProvider 
} from '../api/providers';

const ProviderSettings = () => {
    const [models, setModels] = useState([]);
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [preflightMsg, setPreflightMsg] = useState(null);

    const fetchData = async () => {
        setLoading(true);
        try {
            const modelsData = await listProviderModels();
            setModels(modelsData);
            
            const runsData = await listRecentProviderRuns();
            setRuns(runsData);
        } catch (error) {
            console.error("Failed to load provider data", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleToggleEnable = async (modelId, currentState) => {
        try {
            if (currentState) {
                await disableProviderModel(modelId);
            } else {
                await enableProviderModel(modelId);
            }
            await fetchData();
        } catch (error) {
            console.error("Failed to toggle provider status", error);
            alert("Failed to change provider status");
        }
    };

    const handlePreflight = async (provider_name, model_name, modality) => {
        try {
            const res = await preflightProvider({ provider_name, model_name, modality });
            setPreflightMsg({
                ok: res.ok,
                message: `[${model_name}] Preflight: ${res.message}`
            });
            setTimeout(() => setPreflightMsg(null), 5000);
        } catch (error) {
            setPreflightMsg({ ok: false, message: "Preflight request failed." });
            setTimeout(() => setPreflightMsg(null), 5000);
        }
    };

    if (loading) {
        return <div className="p-8">Loading Provider Settings...</div>;
    }

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <h1 className="text-3xl font-bold mb-6 text-gray-800">Provider Settings</h1>
            
            {preflightMsg && (
                <div className={`p-4 mb-6 rounded ${preflightMsg.ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {preflightMsg.message}
                </div>
            )}
            
            <div className="mb-10">
                <h2 className="text-2xl font-semibold mb-4 text-gray-700">Model Catalog</h2>
                <div className="bg-white shadow rounded-lg overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Provider</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model Name</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Modality</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {models.map(model => (
                                <tr key={model.id}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{model.provider_name}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{model.display_name} ({model.model_name})</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{model.modality}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${model.is_enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                            {model.is_enabled ? 'Enabled' : 'Disabled'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                                        <button 
                                            onClick={() => handlePreflight(model.provider_name, model.model_name, model.modality)}
                                            className="text-indigo-600 hover:text-indigo-900"
                                        >
                                            Preflight
                                        </button>
                                        <button 
                                            onClick={() => handleToggleEnable(model.id, model.is_enabled)}
                                            className={model.is_enabled ? "text-red-600 hover:text-red-900" : "text-green-600 hover:text-green-900"}
                                        >
                                            {model.is_enabled ? 'Disable' : 'Enable'}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div>
                <h2 className="text-2xl font-semibold mb-4 text-gray-700">Recent Provider Runs</h2>
                <div className="bg-white shadow rounded-lg overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Operation</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Context</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {runs.map(run => (
                                <tr key={run.id}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(run.created_at).toLocaleString()}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{run.operation}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{run.provider_name}/{run.model_name}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {run.project_id && <span className="mr-2">Proj: {run.project_id}</span>}
                                        {run.scene_id && <span>Scene: {run.scene_id}</span>}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{run.status}</td>
                                </tr>
                            ))}
                            {runs.length === 0 && (
                                <tr>
                                    <td colSpan="5" className="px-6 py-4 text-center text-sm text-gray-500">No recent runs found.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
            
        </div>
    );
};

export default ProviderSettings;
