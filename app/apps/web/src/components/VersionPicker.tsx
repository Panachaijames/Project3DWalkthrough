// The version picker (DESIGN.md 15.3): a shadcn Select of the project's versions, newest first, each as
// `v2 · 29 Oct 2026 · c3a9408304a2` (its label as the tooltip); choosing one navigates to it, keeping the address options.
// While a picked version is still loading, the picker shows that one, and picking the version on screen again goes back
// to it (the router then drops the pending load): the last pick wins (fix step, review finding "adversarial" 2; before,
// that pick did nothing and the page landed on the version turned away from). Closing the list hands the keyboard back to
// the viewer (finding "adversarial" 9).
import { useLocation, useNavigate, useNavigation } from 'react-router';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { VersionSummary } from '@/api/generated/types.gen';
import { versionLabel } from '@/lib/format';

export interface VersionPickerProps {
  projectId: string;
  versions: readonly VersionSummary[];
  current: number;
}

/** The version a navigation is going to, when it is a version page of this project. */
export function versionOf(pathname: string | undefined, projectId: string): number | null {
  if (!pathname) return null;
  const m = /^\/projects\/([^/]+)\/v\/([1-9]\d{0,8})\/?$/.exec(pathname);
  return m && m[1] === projectId ? Number(m[2]) : null;
}

export function VersionPicker({ projectId, versions, current }: VersionPickerProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const navigation = useNavigation();
  const pending = navigation.state === 'loading' ? versionOf(navigation.location?.pathname, projectId) : null;
  const shown = pending ?? current;
  const newestFirst = [...versions].sort((a, b) => b.version - a.version);
  const shownInfo = versions.find(v => v.version === shown);
  return (
    <Select
      value={String(shown)}
      onValueChange={value => {
        const n = Number(value);
        if (n === shown) return;
        // back to the version on screen: replace (no second history entry for it); the pending load is dropped
        navigate(`/projects/${projectId}/v/${value}${location.search}`, n === current ? { replace: true } : undefined);
      }}
    >
      <SelectTrigger size="sm" aria-label="Version" data-testid="version-picker" data-pending={pending !== null ? '' : undefined} title={shownInfo?.label}>
        <SelectValue placeholder={`v${shown}`} />
      </SelectTrigger>
      <SelectContent position="popper" align="end" onCloseAutoFocus={e => e.preventDefault()}>
        {newestFirst.map(v => (
          <SelectItem key={v.version} value={String(v.version)} title={v.label} data-testid="version-option" data-version={v.version}>
            {versionLabel(v)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
