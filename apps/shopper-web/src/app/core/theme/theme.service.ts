import { Injectable, signal } from '@angular/core';

export type ShopperTheme = 'default' | 'midnight' | 'emerald' | 'ruby' | 'cyberpunk' | 'amber';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_KEY = 'shopper_web_theme';
  
  // Current theme signal
  currentTheme = signal<ShopperTheme>('default');

  constructor() {
    const saved = localStorage.getItem(this.THEME_KEY) as ShopperTheme;
    if (saved) {
      this.setTheme(saved);
    }
  }

  setTheme(theme: ShopperTheme) {
    this.currentTheme.set(theme);
    localStorage.setItem(this.THEME_KEY, theme);
    
    // Apply to DOM
    document.documentElement.setAttribute('data-theme', theme);
  }

  toggleDarkMode() {
    const next = this.currentTheme() === 'midnight' ? 'default' : 'midnight';
    this.setTheme(next);
  }
}
