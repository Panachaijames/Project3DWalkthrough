// Not found (DESIGN.md 15.1 `*`), and the routes' error boundary: an API 404 (project_not_found, version_not_found) or a
// bad address shows Not found; anything else an Alert with the reason and Retry (the router runs the loaders again).
import { CircleAlert, RotateCw } from 'lucide-react';
import { Link, useRevalidator, useRouteError } from 'react-router';
import { AppBar } from '@/components/AppBar';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { errorReason, errorTitle, notFoundTitle } from '@/lib/format';
import { isNotFoundError, notFoundMessage } from '@/lib/routeData';
import { useDocumentTitle } from '@/lib/useDocumentTitle';

export function NotFound({ message }: { message?: string }) {
  useDocumentTitle(notFoundTitle());
  return (
    <div className="min-h-svh bg-muted/30">
      <AppBar className="sticky top-0" />
      <main className="mx-auto max-w-2xl px-6 py-16" data-testid="not-found">
        <h1 className="text-xl font-semibold">Not found</h1>
        <p className="mt-2 text-muted-foreground" data-testid="not-found-message">
          {message ?? 'There is no page at this address.'}
        </p>
        <Button asChild variant="outline" className="mt-6">
          <Link to="/projects">Back to projects</Link>
        </Button>
      </main>
    </div>
  );
}

export function RouteError() {
  const error = useRouteError();
  const revalidator = useRevalidator();
  useDocumentTitle(isNotFoundError(error) ? notFoundTitle() : errorTitle());
  if (isNotFoundError(error)) return <NotFound message={notFoundMessage(error)} />;
  const busy = revalidator.state !== 'idle';
  return (
    <div className="min-h-svh bg-muted/30">
      <AppBar className="sticky top-0" />
      <main className="mx-auto max-w-2xl px-6 py-16">
        <Alert variant="destructive" data-testid="route-error">
          <CircleAlert aria-hidden="true" />
          <AlertTitle>This page could not be loaded</AlertTitle>
          <AlertDescription>
            <p data-testid="route-error-reason">{errorReason(error)}</p>
            <div className="mt-2 flex gap-2">
              <Button size="sm" variant="outline" disabled={busy} onClick={() => void revalidator.revalidate()} data-testid="route-error-retry">
                <RotateCw aria-hidden="true" className={busy ? 'animate-spin' : undefined} />
                Retry
              </Button>
              <Button size="sm" variant="ghost" asChild>
                <Link to="/projects">Back to projects</Link>
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      </main>
    </div>
  );
}
