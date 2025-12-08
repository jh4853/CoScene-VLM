/**
 * WebSocket Message Type Definitions (for Phase 2)
 */

export type WebSocketMessageType =
  | 'edit_request'
  | 'status'
  | 'progress'
  | 'usd_generated'
  | 'frames_rendered'
  | 'verification_complete'
  | 'complete'
  | 'error'
  | 'ping'
  | 'pong';

export interface BaseWebSocketMessage {
  type: WebSocketMessageType;
}

// Client → Server Messages
export interface EditRequestMessage extends BaseWebSocketMessage {
  type: 'edit_request';
  content: string;
  messageId?: string;
}

export interface PingMessage extends BaseWebSocketMessage {
  type: 'ping';
  timestamp: number;
}

// Server → Client Messages
export interface StatusMessage extends BaseWebSocketMessage {
  type: 'status';
  status: 'processing' | 'complete' | 'failed';
  message: string;
}

export interface ProgressMessage extends BaseWebSocketMessage {
  type: 'progress';
  step: string;
  message: string;
  progress?: number; // 0-100
}

export interface USDGeneratedMessage extends BaseWebSocketMessage {
  type: 'usd_generated';
  usd_patch: string;
}

export interface FramesRenderedMessage extends BaseWebSocketMessage {
  type: 'frames_rendered';
  frames: Record<string, string>; // angle → url
}

export interface VerificationCompleteMessage extends BaseWebSocketMessage {
  type: 'verification_complete';
  passed: boolean;
  errors: string[];
}

export interface CompleteMessage extends BaseWebSocketMessage {
  type: 'complete';
  renders: Record<string, string>;
  message: string;
  metadata?: Record<string, any>;
}

export interface ErrorMessage extends BaseWebSocketMessage {
  type: 'error';
  error_code: string;
  message: string;
}

export interface PongMessage extends BaseWebSocketMessage {
  type: 'pong';
  timestamp: number;
}

export type WebSocketMessage =
  | EditRequestMessage
  | PingMessage
  | StatusMessage
  | ProgressMessage
  | USDGeneratedMessage
  | FramesRenderedMessage
  | VerificationCompleteMessage
  | CompleteMessage
  | ErrorMessage
  | PongMessage;
