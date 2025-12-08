/**
 * API Type Definitions for CoScene Backend
 */

// Session Types
export interface Session {
  id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface CreateSessionRequest {
  user_id: string;
  metadata?: Record<string, any>;
}

export interface CreateSessionResponse {
  id: string;
  user_id: string;
  created_at: string;
  message: string;
}

// Scene Edit Types
export interface EditSceneRequest {
  prompt: string;
  session_id: string;
}

export interface EditSceneResponse {
  message: string;
  session_id: string;
  scene_version_id: string;
  usd_content?: string;
  renders?: Record<string, string>; // camera_angle -> render_id
  metadata?: {
    usd_patch?: string;
    objects_added?: string[];
    objects_modified?: string[];
  };
}

export interface RenderInfo {
  id: string;
  angle?: string;
  url?: string;
  created_at?: string;
}

// Scene Version Types
export interface SceneVersion {
  id: string;
  session_id: string;
  version_number: number;
  usd_content: string;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface SceneVersionsResponse {
  session_id: string;
  versions: SceneVersion[];
}

// Message Types
export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  extra_metadata?: Record<string, any>;
}

// Health Check Types
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  checks: Record<string, boolean>;
}

// Error Types
export interface APIError {
  detail: string;
  error_code?: string;
  status_code: number;
}
