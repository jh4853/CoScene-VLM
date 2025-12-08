/**
 * Custom Message Component for Chat
 * Displays user and assistant messages with renders
 * User messages: bg-blue-500, Assistant messages: bg-gray-100
 */

import { clsx } from 'clsx';
import type { CoSceneMessage } from '../../services/runtime';

interface CustomMessageProps {
  message: CoSceneMessage;
}

export function CustomMessage({ message }: CustomMessageProps) {
  const isUser = message.role === 'user';
  const isLoading = message.metadata?.isLoading;

  return (
    <div className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={clsx(
          'max-w-[85%] rounded-2xl px-5 py-4 shadow-sm',
          isUser ? 'text-white' : 'text-gray-900',
          isLoading && 'animate-pulse'
        )}
        style={{
          backgroundColor: isUser ? '#3b82f6' : '#f3f4f6',
          padding: '10px',
          margin: '10px',
          borderRadius: '10px',
        }}
      >
        {/* Message content */}
        <div className="whitespace-pre-wrap break-words leading-relaxed flex items-center gap-2">
          {message.content}
          {isLoading && (
            <span className="inline-flex gap-1">
              <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </span>
          )}
        </div>

        {/* Error indicator */}
        {message.metadata?.error && (
          <div className={clsx("mt-2 text-xs", isUser ? "text-red-200" : "text-red-600")}>An error occurred</div>
        )}

        {/* Renders */}
        {/* {message.metadata?.renders && Object.keys(message.metadata.renders).length > 0 && (
          <div className="mt-3 space-y-2">
            <div className={clsx("text-xs font-medium", isUser ? "text-blue-100" : "text-gray-500")}>Rendered views:</div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(message.metadata.renders).map(([angle, render]) => (
                <div key={render.id} className="relative">
                  <img
                    src={render.url}
                    alt={angle || 'Scene render'}
                    className="w-full rounded-lg border border-gray-200 shadow-sm"
                    loading="lazy"
                  />
                  {angle && (
                    <div className="absolute bottom-1.5 left-1.5 bg-black bg-opacity-60 text-white text-xs px-2 py-0.5 rounded">
                      {angle}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )} */}

        {/* USD Patch (collapsible code block) */}
        {message.metadata?.usdPatch && (
          <details className="mt-3">
            <summary className={clsx("text-xs font-medium cursor-pointer", isUser ? "text-blue-100 hover:text-white" : "text-gray-500 hover:text-gray-700")}>
              View USD changes
            </summary>
            <pre className={clsx("mt-2 text-xs p-3 rounded-lg overflow-x-auto", isUser ? "bg-blue-600 bg-opacity-40" : "bg-white border border-gray-200")}>
              <code>{message.metadata.usdPatch}</code>
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}
