// The app's TanStack Query client (DESIGN.md 15.1): staleTime 30 s, one retry.
import { QueryClient } from '@tanstack/react-query';

export function createQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } });
}
