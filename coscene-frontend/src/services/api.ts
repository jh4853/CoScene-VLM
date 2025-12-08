/**
 * API Client for CoScene Backend
 */

import type {
  CreateSessionRequest,
  CreateSessionResponse,
  EditSceneRequest,
  EditSceneResponse,
  SceneVersionsResponse,
  Message,
  HealthResponse,
  APIError,
} from '../types/api.types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Generic fetch wrapper with error handling
   */
  private async fetch<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        const error: APIError = await response.json().catch(() => ({
          detail: response.statusText,
          status_code: response.status,
        }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // ============ Session Endpoints ============

  /**
   * Create a new editing session
   */
  async createSession(
    request: CreateSessionRequest
  ): Promise<CreateSessionResponse> {
    return this.fetch<CreateSessionResponse>('/sessions', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Get session by ID
   */
  async getSession(sessionId: string): Promise<CreateSessionResponse> {
    return this.fetch<CreateSessionResponse>(`/sessions/${sessionId}`);
  }

  /**
   * Delete session
   */
  async deleteSession(sessionId: string): Promise<void> {
    return this.fetch<void>(`/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Get chat history for a session
   */
  async getChatHistory(sessionId: string, limit: number = 100): Promise<Message[]> {
    return this.fetch<Message[]>(`/sessions/${sessionId}/history?limit=${limit}`);
  }

  // ============ Scene Editing Endpoints ============

  /**
   * Edit scene with natural language prompt
   */
  async editScene(request: EditSceneRequest): Promise<EditSceneResponse> {
    return this.fetch<EditSceneResponse>(
      `/sessions/${request.session_id}/edit`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      }
    );
  }

  /**
   * Get current USD scene content
   */
  async getScene(sessionId: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/scene`);
    if (!response.ok) {
      throw new Error(`Failed to fetch scene: ${response.statusText}`);
    }
    return response.text();
  }

  /**
   * Get scene version history
   */
  async getSceneVersions(sessionId: string): Promise<SceneVersionsResponse> {
    return this.fetch<SceneVersionsResponse>(`/sessions/${sessionId}/versions`);
  }

  // ============ Render Endpoints ============

  /**
   * Get render image URL
   */
  getRenderUrl(renderId: string): string {
    return `${this.baseUrl}/renders/${renderId}`;
  }

  /**
   * Fetch render image as blob
   */
  async getRenderBlob(renderId: string): Promise<Blob> {
    const response = await fetch(this.getRenderUrl(renderId));
    if (!response.ok) {
      throw new Error(`Failed to fetch render: ${response.statusText}`);
    }
    return response.blob();
  }

  // ============ Health Check Endpoints ============

  /**
   * Check service health
   */
  async healthCheck(): Promise<HealthResponse> {
    return this.fetch<HealthResponse>('/health');
  }

  /**
   * Check service readiness
   */
  async readyCheck(): Promise<HealthResponse> {
    return this.fetch<HealthResponse>('/ready');
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// Export class for testing
export { APIClient };
