// U7: colours.ts (docs/upload/DESIGN.md U-12.1: "the role's colour, `other` and `ignore` faint"; ACCEPTANCE 2.3 U7
// "colours per role").
import { describe, expect, it } from 'vitest';
import type { PartKind } from '@walkthrough/viewer';
import {
  FLAG_COLOUR, OPENING_COLOUR, PART_FILL, ROLE_STROKE, ROLES, rgba, roleStroke,
} from '@/plan/colours';
import type { LayerRole } from '@/upload/contracts';

const ALL_ROLES: LayerRole[] = ['wall', 'column', 'glass', 'window', 'door', 'screen', 'stair', 'stair-above', 'railing',
  'furniture', 'room-name', 'room-outline', 'level', 'grid', 'light', 'other', 'ignore'];
const PART_KINDS: PartKind[] = ['wall', 'column', 'lintel', 'sill', 'parapet', 'glass', 'mullion', 'railing', 'single', 'step', 'slab',
  'pane', 'balustrade', 'low', 'builtin', 'deck', 'post', 'tread', 'landing', 'ceiling'];

describe('colours per role', () => {
  it('every one of the 17 roles has a colour, an alpha and a width', () => {
    expect([...ROLES].sort()).toEqual([...ALL_ROLES].sort());
    expect(Object.keys(ROLE_STROKE).sort()).toEqual([...ALL_ROLES].sort());
    for (const r of ALL_ROLES) {
      expect(ROLE_STROKE[r].colour).toMatch(/^#[0-9a-f]{6}$/);
      expect(ROLE_STROKE[r].alpha).toBeGreaterThan(0);
      expect(ROLE_STROKE[r].alpha).toBeLessThanOrEqual(1);
    }
  });

  it('`other` and `ignore` are faint (ignore the fainter); every other role is drawn at 0.8 or more', () => {
    expect(ROLE_STROKE.other.alpha).toBeLessThan(0.5);
    expect(ROLE_STROKE.ignore.alpha).toBeLessThan(ROLE_STROKE.other.alpha);
    for (const r of ALL_ROLES.filter(x => x !== 'other' && x !== 'ignore')) expect(ROLE_STROKE[r].alpha, r).toBeGreaterThanOrEqual(0.8);
  });

  it('the roles that are built or read for openings have colours of their own', () => {
    const strong: LayerRole[] = ['wall', 'column', 'glass', 'window', 'door', 'screen', 'stair', 'railing', 'furniture'];
    expect(new Set(strong.map(r => ROLE_STROKE[r].colour)).size).toBe(strong.length);
    expect(new Set(ALL_ROLES.map(r => ROLE_STROKE[r].colour)).size).toBe(ALL_ROLES.length);
  });

  it('the drawing\'s lines are hairlines (at most 1 px: the redraw budget)', () => {
    for (const r of ALL_ROLES) expect(ROLE_STROKE[r].width, r).toBeLessThanOrEqual(1);
  });

  it('an unknown role is drawn as `other`', () => {
    expect(roleStroke('no-such-role')).toBe(ROLE_STROKE.other);
    expect(roleStroke('wall')).toBe(ROLE_STROKE.wall);
  });
});

describe('overlay colours', () => {
  it('a fill for every part kind; a colour per opening kind and flag severity', () => {
    expect(Object.keys(PART_FILL).sort()).toEqual([...PART_KINDS].sort());
    for (const k of PART_KINDS) expect(PART_FILL[k]).toMatch(/^#[0-9a-f]{6}$/);
    expect(new Set(Object.values(OPENING_COLOUR)).size).toBe(3);
    expect(FLAG_COLOUR.check).not.toBe(FLAG_COLOUR.info);
  });

  it('rgba', () => {
    expect(rgba('#ff8000', 0.5)).toBe('rgba(255,128,0,0.5)');
    expect(rgba('red', 0.5)).toBe('red');
  });
});
