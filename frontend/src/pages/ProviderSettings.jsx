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
    const [panelPreflightMsg, setPanelPreflightMsg] = useState(null);
    const [panelInput, setPanelInput] = useState({ provider_name: '', model_name: '', modality: '' });

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

    const handlePanelPreflight = async (e) => {
        e.preventDefault();
        try {
            const res = await preflightProvider(panelInput);
            setPanelPreflightMsg({
                ok: res.ok,
                message: `[${panelInput.model_name}] Preflight: ${res.message}`
            });
            setTimeout(() => setPanelPreflightMsg(null), 5000);
        } catch (error) {
            setPanelPreflightMsg({ ok: false, message: "Preflight request failed." });
            setTimeout(() => setPanelPreflightMsg(null), 5000);
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
                <h2 className="text-2xl font-semibold mb-4 text-gray-700">Test Preflight</h2>
                <div className="bg-white shadow rounded-lg p-6">
                    <form onSubmit={handlePanelPreflight} className="flex flex-col space-y-4 max-w-md">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Provider Name</label>
                            <input 
                                type="text" 
                                className="w-full border-gray-300 rounded-md shadow-sm p-2 border" 
                                value={panelInput.provider_name} 
                                onChange={(e) => setPanelInput({...panelInput, provider_name: e.target.value})} 
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Model Name</label>
                            <input 
                                type="text" 
                                className="w-full border-gray-300 rounded-md shadow-sm p-2 border" 
                                value={panelInput.model_name} 
                                onChange={(e) => setPanelInput({...panelInput, model_name: e.target.value})} 
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Modality</label>
                            <input 
                                type="text" 
                                className="w-full border-gray-300 rounded-md shadow-sm p-2 border" 
                                value={panelInput.modality} 
                                onChange={(e) => setPanelInput({...panelInput, modality: e.target.value})} 
                                required
                            />
                        </div>
                        <button type="submit" className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 w-full sm:w-auto self-start">
                            Run Preflight
                        </button>
                        
                        {panelPreflightMsg && (
                            <div className={`p-4 mt-4 rounded ${panelPreflightMsg.ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                {panelPreflightMsg.message}
                            </div>
                        )}
                    </form>
                </div>
            </div>

            <div className="mb-10">
                <h2 className="text-2xl font-semibold mb-4 text-gray-700">Model Catalog</h2>
                <div className="bg-white shadow rounded-lg overflow-hidden overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Provider</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model Name</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Display Name</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Modality</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Is Mock</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cost Hint</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Aspect Ratios</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Durations</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {models.map(model => (
                                <tr key={model.id}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{model.provider_name}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{model.model_name}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{model.display_name}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{model.modality}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{model.is_mock ? 'Yes' : 'No'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{model.cost_hint || '-'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{model.supports_aspect_ratio || '-'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{model.supports_duration_seconds || '-'}</td>
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
