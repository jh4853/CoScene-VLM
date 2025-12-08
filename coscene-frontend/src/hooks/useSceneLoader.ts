/**
 * Scene Loading Hook
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../services/api';

interface UseSceneLoaderResult {
  usdContent: string | null;
  loading: boolean;
  error: Error | null;
  loadScene: (sessionId: string) => Promise<void>;
}

/**
 * Hook to load USD scene content from backend
 */
export function useSceneLoader(): UseSceneLoaderResult {
  const [usdContent, setUsdContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadScene = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);

    try {
      const content = await apiClient.getScene(sessionId);
      setUsdContent(content);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to load scene');
      setError(error);
      console.error('Scene loading error:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    usdContent,
    loading,
    error,
    loadScene,
  };
}
