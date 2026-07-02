import React from "react";
import { Routes, Route } from "react-router-dom";
import AppShell from "./components/AppShell";
import Dashboard from "./pages/Dashboard";
import CreateProject from "./pages/CreateProject";
import ProjectDetail from "./pages/ProjectDetail";
import ScriptReview from "./pages/ScriptReview";

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects/new" element={<CreateProject />} />
        <Route path="/projects/:projectId" element={<ProjectDetail />} />
        <Route path="/projects/:projectId/script" element={<ScriptReview />} />
      </Routes>
    </AppShell>
  );
}

export default App;
