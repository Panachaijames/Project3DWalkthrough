// Playwright globalTeardown: releases the machine-wide Edge lock taken by global-setup.ts (same process).
import { release } from '../../tools/edge-lock.mjs';

export default async function globalTeardown(): Promise<void> {
  release();
}
