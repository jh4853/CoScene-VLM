import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import App from './App.tsx';
import { SessionRedirect } from './components/SessionRedirect';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionRedirect />} />
        <Route path="/:sessionId" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
