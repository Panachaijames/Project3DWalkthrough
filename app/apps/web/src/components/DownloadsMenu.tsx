// The Downloads menu (DESIGN.md 15.3): `3ds Max script (.ms)`, `Furniture list (CSV)`, `Offline viewer (HTML)`, each a
// plain <a href download> to the URL the version detail gives (the API sends the file with the saved heights), disabled
// when the version has none. Not modal: no scroll lock, the viewer stays as it is while the menu is open.
// The CSV and the offline file carry the SAVED heights (15.5): opening the menu sends a debounced save at once (onOpen),
// and while a save is going, or has failed (the files would then carry other heights than the viewer shows), those two
// wait, disabled, with the reason. Opening the menu also asks the API whether it answers: when it does not, every item is
// disabled with that reason, rather than ending in the browser's own failed-download notice (fix step, review findings
// "adversarial" 4 and 6). Closing the menu hands the keyboard back to the viewer (no focus left on the button: W A S D and
// Space go to Walk again; fix step, finding "adversarial" 9).
// Step BX (docs/boxes/DESIGN.md 4): the three files leave the deleted furniture boxes out. The CSV and the offline file
// wait for any unsaved furniture change (heights or deleted boxes) as before; the 3ds Max script, which carries no saved
// heights, waits only while deleted boxes are unsaved (the saver's editsUnsaved), each with its own tooltip.
import { Download, FileCode, FileSpreadsheet, FileText } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { apiUrl, isUnreachable } from '@/api/client';
import { health } from '@/api/generated/sdk.gen';
import type { VersionDownloads } from '@/api/generated/types.gen';
import {
  API_DOWN_TITLE, DOWNLOAD_ITEMS, EDITS_PENDING_TITLE, editsNotSavedTitle, HEIGHTS_PENDING_TITLE, heightsNotSavedTitle,
} from '@/lib/format';
import type { SaverState } from '@/lib/useHeightsSaver';

type DownloadKey = (typeof DOWNLOAD_ITEMS)[number]['key'];

const ICONS: Record<DownloadKey, ReactNode> = {
  maxScript: <FileCode aria-hidden="true" />,
  furnitureCsv: <FileSpreadsheet aria-hidden="true" />,
  offlineHtml: <FileText aria-hidden="true" />,
};

/** The downloads made with the saved furniture heights (and deleted boxes). */
const WITH_HEIGHTS: ReadonlySet<DownloadKey> = new Set<DownloadKey>(['furnitureCsv', 'offlineHtml']);
/** The download that carries no saved heights but leaves the saved deleted boxes out (step BX): it waits for those only. */
const WITH_EDITS: ReadonlySet<DownloadKey> = new Set<DownloadKey>(['maxScript']);

/** Does the API answer? (The health route; any answer but "none" counts.) */
export async function apiAnswers(): Promise<boolean> {
  try {
    await health({ throwOnError: true });
    return true;
  } catch (err) {
    return !isUnreachable(err);
  }
}

export interface DownloadsMenuProps {
  downloads: VersionDownloads;
  /**
   * The heights saver's state (null: the version has no furniture). Saving or failed: the CSV and the offline file wait;
   * with editsUnsaved (deleted boxes not saved yet) the Max script waits too.
   */
  heights?: SaverState | null;
  /** The menu opened (the page sends a debounced heights save now). */
  onOpen?: () => void;
  /** Tests: the API check (default: GET /api/health). */
  probe?: () => Promise<boolean>;
}

export function DownloadsMenu({ downloads, heights = null, onOpen, probe = apiAnswers }: DownloadsMenuProps) {
  const [apiDown, setApiDown] = useState(false);
  const down = apiDown || !!heights?.unreachable;
  const waitTitle = heights?.status === 'saving' ? HEIGHTS_PENDING_TITLE
    : heights?.status === 'error' ? heightsNotSavedTitle(heights.reason ?? 'unknown error') : null;
  const editsTitle = !heights?.editsUnsaved ? null
    : heights.status === 'error' ? editsNotSavedTitle(heights.reason ?? 'unknown error') : EDITS_PENDING_TITLE;
  const titleOf = (key: DownloadKey) => (WITH_HEIGHTS.has(key) ? waitTitle : WITH_EDITS.has(key) ? editsTitle : null);
  return (
    <DropdownMenu
      modal={false}
      onOpenChange={open => {
        if (!open) return;
        onOpen?.();
        void probe().then(ok => setApiDown(!ok), () => setApiDown(false));
      }}
    >
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" data-testid="downloads-menu">
          <Download aria-hidden="true" />
          Downloads
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="min-w-56"
        data-testid="downloads-list"
        data-api-down={down ? '' : undefined}
        onCloseAutoFocus={e => e.preventDefault()}
      >
        {DOWNLOAD_ITEMS.map(({ key, text }) => {
          const info = downloads[key];
          const waiting = !!info && !down && titleOf(key) !== null;
          if (!info || waiting || down) {
            return (
              <DropdownMenuItem
                key={key}
                disabled
                data-download={key}
                data-waiting={waiting ? '' : undefined}
                title={!info ? undefined : down ? API_DOWN_TITLE : titleOf(key) ?? undefined}
              >
                {ICONS[key]}
                {text}
              </DropdownMenuItem>
            );
          }
          return (
            <DropdownMenuItem key={key} asChild data-download={key}>
              <a href={apiUrl(info.url)} download={info.fileName} title={info.fileName}>
                {ICONS[key]}
                {text}
              </a>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
