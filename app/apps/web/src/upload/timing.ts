// The Build page's two clocks (docs/upload/DESIGN.md U-14.2): the settings saver's debounce (800 ms) and the build poll
// (1 s while a run is queued or running). One mutable object so that page tests can shorten both; the app never
// changes them.
import { SETTINGS_DEBOUNCE_MS } from './settingsSaver';
import { POLL_MS } from './useBuild';

export const timing = { settingsDebounceMs: SETTINGS_DEBOUNCE_MS, pollMs: POLL_MS };
