/**
 * Session Management Hook
 */

import { useState, useEffect } from 'react';
import { apiClient } from '../services/api';
import type { CreateSessionResponse } from '../types/api.types';

const DEFAULT_USER_ID =
  import.meta.env.VITE_DEFAULT_USER_ID || '00000000-0000-0000-0000-000000000001';

interface UseSessionResult {
  session: CreateSessionResponse | null;
  sessionId: string | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

interface UseSessionOptions {
  /**
   * Optional existing session ID to load.
   * If not provided, a new session will be created.
   */
  sessionId?: string;
}

/**
 * Hook to manage CoScene session lifecycle
 * - If sessionId is provided, loads the existing session
 * - If sessionId is not provided, creates a new session
 */
export function useSession(options?: UseSessionOptions): UseSessionResult {
  const [session, setSession] = useState<CreateSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const createSession = async () => {
    setLoading(true);
    setError(null);

    try {
      const newSession = await apiClient.createSession({
        user_id: DEFAULT_USER_ID,
      });

      setSession(newSession);
      console.log('Session created:', newSession.id);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create session');
      setError(error);
      console.error('Session creation error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSession = async (sessionId: string) => {
    setLoading(true);
    setError(null);

    try {
      const existingSession = await apiClient.getSession(sessionId);
      setSession(existingSession);
      console.log('Session loaded:', existingSession.id);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to load session');
      setError(error);
      console.error('Session loading error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (options?.sessionId) {
      loadSession(options.sessionId);
    } else {
      createSession();
    }
  }, [options?.sessionId]);

  return {
    session,
    sessionId: session?.id || null,
    loading,
    error,
    refetch: options?.sessionId
      ? () => loadSession(options.sessionId!)
      : createSession,
  };
}
