/**
 * Main App Component
 * Integrates session management, chat runtime, and 3D viewer
 */

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AppLayout } from './components/Layout/AppLayout';
import { ChatPanel } from './components/ChatPanel/ChatPanel';
import { SceneViewer } from './components/SceneViewer/SceneViewer';
import { useSession } from './hooks/useSession';
import { useSceneLoader } from './hooks/useSceneLoader';
import { createCoSceneRuntime, CoSceneRuntime } from './services/runtime';

export default function App() {
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>();
  const { sessionId, loading: sessionLoading, error: sessionError } = useSession({
    sessionId: urlSessionId,
  });
  const { usdContent: initialUsdContent, loadScene } = useSceneLoader();
  const [runtime, setRuntime] = useState<CoSceneRuntime | null>(null);
  const [currentUsdContent, setCurrentUsdContent] = useState<string | null>(null);

  // Create runtime when session is ready
  useEffect(() => {
    if (sessionId) {
      const newRuntime = createCoSceneRuntime(sessionId);
      setRuntime(newRuntime);

      // Load initial scene
      loadScene(sessionId).catch(console.error);

      // Load message history if this is an existing session (has URL param)
      if (urlSessionId) {
        newRuntime.loadHistory().catch((err) => {
          console.error('Failed to load message history:', err);
        });
      }
    }
  }, [sessionId, loadScene, urlSessionId]);

  // Update USD content from initial load
  useEffect(() => {
    if (initialUsdContent) {
      setCurrentUsdContent(initialUsdContent);
    }
  }, [initialUsdContent]);

  // Subscribe to runtime messages to extract latest USD content
  useEffect(() => {
    if (!runtime) return;

    const unsubscribe = runtime.subscribe((messages) => {
      // Find the latest assistant message with USD content
      for (let i = messages.length - 1; i >= 0; i--) {
        const message = messages[i];
        if (message.role === 'assistant' && message.metadata?.usdContent) {
          setCurrentUsdContent(message.metadata.usdContent);
          break;
        }
      }
    });

    return unsubscribe;
  }, [runtime]);

  // Loading state
  if (sessionLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950 text-white">
        <div className="text-center">
          <div className="mb-4">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-600 border-t-blue-500"></div>
          </div>
          <div>Creating session...</div>
        </div>
      </div>
    );
  }

  // Error state
  if (sessionError) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950 text-white">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold mb-2">Failed to Create Session</h2>
          <p className="text-gray-400 mb-4">{sessionError.message}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Main app
  if (!runtime || !sessionId) {
    return null;
  }

  return (
    <AppLayout
      sessionId={sessionId}
      chatPanel={<ChatPanel runtime={runtime} />}
      sceneViewer={<SceneViewer usdContent={currentUsdContent} />}
    />
  );
}
