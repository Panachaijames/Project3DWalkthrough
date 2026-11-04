// Types for tools/edge-lock.mjs (used by the Playwright globalSetup / globalTeardown).
export declare const LOCK_FILE: string;
export interface EdgeLockHolder { step: string; pid: number; startedAt: string }
export declare function holder(): EdgeLockHolder | null;
export declare function acquire(step: string, opts?: { waitMs?: number; pollMs?: number }): Promise<void>;
export declare function release(): void;
