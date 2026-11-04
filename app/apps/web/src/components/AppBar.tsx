// The staff app's 48 px bar (DESIGN.md 15.3): back to the projects (or the app's name on the list), a title, the page's
// controls on the right, and a thin progress line while the router loads the next page.
import { ArrowLeft } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link, useNavigation } from 'react-router';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { APP_NAME } from '@/lib/format';

export interface AppBarProps {
  /** Shown after the back link (the project's name); drawing text, rendered as text. */
  title?: ReactNode;
  /** A 'Projects' back link instead of the app's name. */
  back?: boolean;
  /** Right-hand controls (version picker, downloads, heights status). */
  children?: ReactNode;
  className?: string;
}

export function AppBar({ title, back = false, children, className }: AppBarProps) {
  const navigation = useNavigation();
  const busy = navigation.state !== 'idle';
  return (
    <header
      data-testid="app-bar"
      className={cn('relative z-20 flex h-12 shrink-0 items-center gap-2 border-b bg-background px-3 text-foreground', className)}
    >
      {back ? (
        <Button asChild variant="ghost" size="sm" className="shrink-0">
          <Link to="/projects" data-testid="back-to-projects">
            <ArrowLeft aria-hidden="true" />
            Projects
          </Link>
        </Button>
      ) : (
        <Link to="/projects" className="shrink-0 px-2 text-sm font-semibold tracking-tight" data-testid="app-name">
          {APP_NAME}
        </Link>
      )}
      {title !== undefined && (
        <>
          <Separator orientation="vertical" className="mx-1 data-[orientation=vertical]:h-5" />
          <div className="min-w-0 flex-1 truncate text-sm font-medium" data-testid="app-bar-title">
            {title}
          </div>
        </>
      )}
      {title === undefined && <div className="flex-1" />}
      <div className="flex shrink-0 items-center gap-2">{children}</div>
      {busy && (
        <div
          role="progressbar"
          aria-label="Loading"
          data-testid="navigation-progress"
          className="pointer-events-none absolute inset-x-0 top-12 h-0.5 animate-pulse bg-primary/60"
        />
      )}
    </header>
  );
}
