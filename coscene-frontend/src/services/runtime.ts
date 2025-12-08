/**
 * Simple message store for CoScene
 * Phase 1: HTTP-based communication with backend
 * Note: This is a placeholder until we properly integrate assistant-ui
 */

import { apiClient } from './api';
import type { EditSceneResponse } from '../types/api.types';

export interface CoSceneMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: Date;
  metadata?: {
    renders?: Record<string, { id: string; url?: string; angle?: string }>;
    usdPatch?: string;
    usdContent?: string;
    sceneVersionId?: string;
    error?: boolean;
    isLoading?: boolean;
  };
}

export class CoSceneRuntime {
  private messages: CoSceneMessage[] = [];
  private sessionId: string;
  private listeners: Array<(messages: CoSceneMessage[]) => void> = [];

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }
  

  subscribe(listener: (messages: CoSceneMessage[]) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  getMessages() {
    return this.messages;
  }

  private notify() {
    this.listeners.forEach((listener) => listener([...this.messages]));
  }

  /**
   * Load message history from the backend
   * Converts API Message format to CoSceneMessage format
   */
  async loadHistory() {
    try {
      const apiMessages = await apiClient.getChatHistory(this.sessionId);

      // Convert API messages to CoSceneMessage format
      const coSceneMessages: CoSceneMessage[] = apiMessages.map((msg) => {
        // Process metadata to add render URLs if renders exist
        let metadata = msg.extra_metadata;
        if (metadata?.renders && typeof metadata.renders === 'object') {
          // If renders is a Record<string, string> (angle -> renderId)
          const renders = Object.entries(metadata.renders as Record<string, string>).reduce(
            (acc, [angle, renderId]) => {
              acc[angle] = {
                id: renderId,
                url: apiClient.getRenderUrl(renderId),
                angle: angle,
              };
              return acc;
            },
            {} as Record<string, { id: string; url?: string; angle?: string }>
          );
          metadata = { ...metadata, renders };
        }

        return {
          id: msg.id,
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          createdAt: new Date(msg.timestamp),
          metadata,
        };
      });

      // Replace current messages with loaded history
      this.messages = coSceneMessages;
      this.notify();

      console.log(`Loaded ${coSceneMessages.length} messages from history`);
    } catch (error) {
      console.error('Failed to load message history:', error);
      throw error;
    }
  }

  async sendMessage(content: string) {
    // Add user message
    const userMessage: CoSceneMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      createdAt: new Date(),
    };
    this.messages.push(userMessage);
    this.notify();

    // Add placeholder loading message
    const loadingMessageId = crypto.randomUUID();
    const loadingMessage: CoSceneMessage = {
      id: loadingMessageId,
      role: 'assistant',
      content: 'Generating USD Patch.',
      createdAt: new Date(),
      metadata: { isLoading: true },
    };
    this.messages.push(loadingMessage);
    this.notify();

    // Animate ellipsis (. -> .. -> ... -> .)
    let ellipsisCount = 1;
    let currentPhase = 'generating'; // 'generating' or 'verifying'
    const ellipsisTimer = setInterval(() => {
      const messageIndex = this.messages.findIndex((m) => m.id === loadingMessageId);
      if (messageIndex !== -1 && this.messages[messageIndex].metadata?.isLoading) {
        ellipsisCount = (ellipsisCount % 3) + 1;
        const ellipsis = '.'.repeat(ellipsisCount);
        const baseText = currentPhase === 'generating' ? 'Generating USD Patch' : 'Verifying USD Update';
        this.messages[messageIndex] = {
          ...this.messages[messageIndex],
          content: `${baseText}${ellipsis}`,
        };
        this.notify();
      }
    }, 250);

    // Update to "Verifying USD Update..." after 5 seconds
    const verifyTimer = setTimeout(() => {
      const messageIndex = this.messages.findIndex((m) => m.id === loadingMessageId);
      if (messageIndex !== -1 && this.messages[messageIndex].metadata?.isLoading) {
        currentPhase = 'verifying';
        ellipsisCount = 0; // Reset so next tick shows "."
        this.messages[messageIndex] = {
          ...this.messages[messageIndex],
          content: 'Verifying USD Update.',
        };
        this.notify();
      }
    }, 5000);

    try {
      // Call backend
      const response: EditSceneResponse = await apiClient.editScene({
        prompt: content,
        session_id: this.sessionId,
      });

      // Clear the timers
      clearTimeout(verifyTimer);
      clearInterval(ellipsisTimer);

      // Format renders with full URLs
      const renders = response.renders
        ? Object.entries(response.renders).reduce((acc, [angle, renderId]) => {
            acc[angle] = {
              id: renderId,
              url: apiClient.getRenderUrl(renderId),
              angle: angle,
            };
            return acc;
          }, {} as Record<string, { id: string; url?: string; angle?: string }>)
        : undefined;

      // Build assistant response
      let assistantContent = response.message || 'Scene updated successfully.';
      // if (renders && Object.keys(renders).length > 0) {
      //   assistantContent += `\n\nRendered scene with ${Object.keys(renders).length} view(s).`;
      // }

      // Replace loading message with actual response
      const messageIndex = this.messages.findIndex((m) => m.id === loadingMessageId);
      if (messageIndex !== -1) {
        this.messages[messageIndex] = {
          id: loadingMessageId,
          role: 'assistant',
          content: assistantContent,
          createdAt: new Date(),
          metadata: {
            renders,
            usdPatch: response.metadata?.usd_patch,
            usdContent: response.usd_content,
            sceneVersionId: response.scene_version_id,
          },
        };
      } else {
        // Fallback: add new message if loading message was somehow removed
        this.messages.push({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: assistantContent,
          createdAt: new Date(),
          metadata: {
            renders,
            usdPatch: response.metadata?.usd_patch,
            usdContent: response.usd_content,
            sceneVersionId: response.scene_version_id,
          },
        });
      }
      this.notify();
    } catch (error) {
      console.error('Scene edit error:', error);

      // Clear the timers
      clearTimeout(verifyTimer);
      clearInterval(ellipsisTimer);

      // Replace loading message with error
      const messageIndex = this.messages.findIndex((m) => m.id === loadingMessageId);
      const errorContent = `Error: ${error instanceof Error ? error.message : 'Failed to process your request.'}`;

      if (messageIndex !== -1) {
        this.messages[messageIndex] = {
          id: loadingMessageId,
          role: 'assistant',
          content: errorContent,
          createdAt: new Date(),
          metadata: { error: true },
        };
      } else {
        // Fallback: add new error message
        this.messages.push({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: errorContent,
          createdAt: new Date(),
          metadata: { error: true },
        });
      }
      this.notify();
    }
  }
}

export function createCoSceneRuntime(sessionId: string): CoSceneRuntime {
  return new CoSceneRuntime(sessionId);
}
