import { Injectable, signal } from '@angular/core';

export const SHOPPER_THEMES = [
  'default', 'midnight', 'emerald', 'ruby',
  'cyberpunk', 'amber', 'lavender', 'ocean',
  'sunset', 'forest', 'slate', 'gold',
] as const;

export type ShopperTheme = (typeof SHOPPER_THEMES)[number];

export function isShopperTheme(x: unknown): x is ShopperTheme {
  return typeof x === 'string' && (SHOPPER_THEMES as readonly string[]).includes(x);
}

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_KEY = 'shopper_web_theme';

  currentTheme = signal<ShopperTheme>('default');

  constructor() {
    const saved = this.readSaved();
    if (saved) {
      this.setTheme(saved, { persist: false });
    }
  }

  /** True when the user picked a theme on this device. */
  hasSavedTheme(): boolean {
    return this.readSaved() !== null;
  }

  setTheme(theme: ShopperTheme, opts: { persist?: boolean } = {}) {
    this.currentTheme.set(theme);
    if (opts.persist ?? true) {
      try {
        localStorage.setItem(this.THEME_KEY, theme);
      } catch {
        // Storage blocked; the theme still applies for this visit.
      }
    }
    document.documentElement.setAttribute('data-theme', theme);
  }

  toggleDarkMode() {
    const next = this.currentTheme() === 'midnight' ? 'default' : 'midnight';
    this.setTheme(next);
  }

  private readSaved(): ShopperTheme | null {
    try {
      const raw = localStorage.getItem(this.THEME_KEY);
      return isShopperTheme(raw) ? raw : null;
    } catch {
      return null;
    }
  }
}
