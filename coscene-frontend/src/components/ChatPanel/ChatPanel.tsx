/**
 * Chat Panel Component
 * Simple chat interface.
 */

import { useState, useEffect, useRef, type FormEvent } from 'react';
import { CustomMessage } from './CustomMessage';
import type { CoSceneRuntime, CoSceneMessage } from '../../services/runtime';

interface ChatPanelProps {
  runtime: CoSceneRuntime;
  className?: string;
}

export function ChatPanel({ runtime, className = '' }: ChatPanelProps) {
  const [messages, setMessages] = useState<CoSceneMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Subscribe to runtime messages
  useEffect(() => {
    const unsubscribe = runtime.subscribe((newMessages) => {
      setMessages(newMessages);
      setIsLoading(false);
    });
    return unsubscribe;
  }, [runtime]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input.trim();
    setInput('');
    setIsLoading(true);

    await runtime.sendMessage(message);
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-12">
            <p className="text-lg mb-2 font-medium">Welcome to CoScene</p>
            <p className="text-sm">Type a prompt to start editing your 3D scene.</p>
            <p className="text-xs mt-4 text-gray-400">Try: "Create a blue sphere in the center"</p>
          </div>
        )}

        {messages.map((message) => (
          <CustomMessage key={message.id} message={message} />
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className=" bg-white p-4 flex-shrink-0">
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe your scene changes..."
            disabled={isLoading}
            className="flex-1 bg-gray-50 text-gray-900 rounded-xl px-4 py-3 border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all"
            style={{ height: '50px' }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-sm"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
