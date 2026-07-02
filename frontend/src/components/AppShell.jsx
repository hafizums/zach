import React from "react";
import { Link } from "react-router-dom";

const AppShell = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
        <Link to="/" className="text-xl font-bold text-gray-900 hover:text-blue-600 transition">
          AI Explainer Shorts Generator
        </Link>
      </header>
      <main className="flex-1 p-6">
        {children}
      </main>
    </div>
  );
};

export default AppShell;
