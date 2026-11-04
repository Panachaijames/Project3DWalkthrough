// Scaffold smoke test of the web test setup (happy-dom, the React plugin, the `@` alias, a shadcn component). Builder F
// owns apps/web/test/** and may keep or replace it.
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { describe, expect, it } from 'vitest';
import { Button } from '@/components/ui/button';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

describe('web test setup', () => {
  it('renders a shadcn Button with React 19 in happy-dom', async () => {
    const host = document.createElement('div');
    document.body.append(host);
    const root = createRoot(host);
    await act(async () => { root.render(<Button variant="outline">Retry</Button>); });
    const button = host.querySelector('button');
    expect(button?.textContent).toBe('Retry');
    expect(button?.getAttribute('data-slot')).toBe('button');
    await act(async () => { root.unmount(); });
    host.remove();
  });
});
