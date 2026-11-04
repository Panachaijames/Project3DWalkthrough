// The staff app's entry (DESIGN.md 15): StrictMode on (the viewer wrapper is built for its double mount, 15.4),
// TanStack Query and the data-mode router.
import { QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router/dom';
import './api/client';
import './index.css';
import { createQueryClient } from './lib/queryClient';
import { startUnsentSender } from './lib/useHeightsSaver';
import { createAppRouter } from './router';

const queryClient = createQueryClient();
const router = createAppRouter(queryClient);
// heights typed earlier and not saved yet (the API did not answer): sent once it does (lib/heightsOutbox.ts)
startUnsentSender(queryClient);

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('index.html has no #root element');

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
