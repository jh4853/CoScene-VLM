/**
 * Main App Layout Component
 * Fixed split-pane layout: Chat (40%) | Scene Viewer (60%)
 */

import type { ReactNode } from 'react';

interface AppLayoutProps {
  sessionId: string | null;
  chatPanel: ReactNode;
  sceneViewer: ReactNode;
}

export function AppLayout({ chatPanel, sceneViewer }: AppLayoutProps) {
  return (
    <div className="flex flex-col h-screen bg-gray-50">

      {/* Main content area with fixed split */}
      <div className="flex-1 flex overflow-hidden min-h-0">

        {/* Chat Panel - 40% width */}
        <div className="w-[30%] border-r border-gray-200 bg-white shadow-sm">
          {chatPanel}
        </div>

        {/* Scene Viewer - 60% width */}
        <div className="w-[70%] bg-gray-50">
          {sceneViewer}
        </div>
        
      </div>
    </div>
  );
}
