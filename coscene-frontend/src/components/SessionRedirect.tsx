/**
 * SessionRedirect Component
 * Creates a new session and redirects to /:sessionId route
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../hooks/useSession';

export function SessionRedirect() {
  const navigate = useNavigate();
  const { sessionId, loading, error } = useSession();

  useEffect(() => {
    if (sessionId) {
      // Redirect to the session route
      navigate(`/${sessionId}`, { replace: true });
    }
  }, [sessionId, navigate]);

  // Loading state
  if (loading) {
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
  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950 text-white">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold mb-2">Failed to Create Session</h2>
          <p className="text-gray-400 mb-4">{error.message}</p>
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

  return null;
}
