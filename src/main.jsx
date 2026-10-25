import React from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/instrument-serif/400.css';
import '@fontsource/instrument-serif/400-italic.css';
import '@fontsource/space-grotesk/300.css';
import '@fontsource/space-grotesk/400.css';
import '@fontsource/space-grotesk/500.css';
import '@fontsource/space-grotesk/700.css';
import './styles.css';
import App from './App.jsx';
import { RouterProvider } from './router.jsx';
import { StudioProvider } from './store.jsx';

createRoot(document.getElementById('root')).render(
  <RouterProvider>
    <StudioProvider>
      <App />
    </StudioProvider>
  </RouterProvider>
);
