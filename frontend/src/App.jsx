import React from "react";
import { Routes, Route } from "react-router-dom";
import AppShell from "./components/AppShell";
import Dashboard from "./pages/Dashboard";
import CreateProject from "./pages/CreateProject";
import ProjectDetail from "./pages/ProjectDetail";
import ScriptReview from "./pages/ScriptReview";
import ScenePlanner from "./pages/ScenePlanner";
import PromptReview from "./pages/PromptReview";
import AssetGeneration from "./pages/AssetGeneration";

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects/new" element={<CreateProject />} />
        <Route path="/projects/:projectId" element={<ProjectDetail />} />
        <Route path="/projects/:projectId/script" element={<ScriptReview />} />
        <Route path="/projects/:projectId/scenes" element={<ScenePlanner />} />
        <Route path="/projects/:projectId/prompts" element={<PromptReview />} />
        <Route path="/projects/:projectId/assets" element={<AssetGeneration />} />
      </Routes>
    </AppShell>
  );
}

export default App;
