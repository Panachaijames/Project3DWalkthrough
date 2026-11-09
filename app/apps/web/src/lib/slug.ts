// Project and office ids from names (docs/upload/DESIGN.md U-13.3, U-8.4), as the API derives them: NFKD, ASCII letters
// and digits, every other run to '-', lower case, cut at a '-' to the limit; '' when fewer than 2 characters are left
// (a Thai name: the API then makes `project-<6 hex>`). Pure: no DOM, no React.

/** A new project id: 2 - 40 characters (U-4.1's path length). */
export const NEW_PROJECT_ID = /^[a-z0-9][a-z0-9-]{1,39}$/;
/** An office id (U-1 contracts). */
export const OFFICE_ID = /^[a-z0-9][a-z0-9-]{1,62}$/;
export const PROJECT_ID_MAX = 40;

export function slugify(name: string, max: number = PROJECT_ID_MAX): string {
  let s = name.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  if (s.length > max) {
    const cut = s.slice(0, max);
    const at = cut.lastIndexOf('-');
    s = (at >= 2 ? cut.slice(0, at) : cut).replace(/-+$/g, '');
  }
  return s.length >= 2 ? s : '';
}

/** Why a typed project id cannot be used, or null. */
export function projectIdProblem(id: string): string | null {
  if (!id) return null;
  if (id.length > PROJECT_ID_MAX) return `at most ${PROJECT_ID_MAX} characters (Windows path length)`;
  if (id.length < 2) return 'at least 2 characters';
  if (!NEW_PROJECT_ID.test(id)) return 'lower-case letters, digits and -, starting with a letter or digit';
  return null;
}
