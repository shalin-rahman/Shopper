import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map } from 'rxjs';
import { TranslocoPipe } from '@ngneat/transloco';

import { AuthService } from './core/auth/auth.service';
import { LocaleService, ShopperLang } from './core/i18n/locale.service';
import { ThemeService, ShopperTheme } from './core/theme/theme.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, TranslocoPipe],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  readonly locale = inject(LocaleService);
  readonly theme = inject(ThemeService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** Pages shown without the staff header and footer. */
  readonly bare = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => /^\/(login|checkout)(\/|\?|$)/.test(e.urlAfterRedirects)),
    ),
    { initialValue: false },
  );

  readonly themes: ShopperTheme[] = [
    'default', 'midnight', 'emerald', 'ruby', 
    'cyberpunk', 'amber', 'lavender', 'ocean', 
    'sunset', 'forest', 'slate', 'gold'
  ];

  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }

  setLang(lang: ShopperLang): void {
    this.locale.setLanguage(lang);
  }

  setTheme(t: ShopperTheme): void {
    this.theme.setTheme(t);
  }

  getThemeColor(t: ShopperTheme): string {
    const colors: Record<string, string> = {
      default: '#6366f1', midnight: '#818cf8', emerald: '#10b981',
      ruby: '#e11d48', cyberpunk: '#ff00ff', amber: '#d97706',
      lavender: '#a855f7', ocean: '#0ea5e9', sunset: '#f97316',
      forest: '#22c55e', slate: '#64748b', gold: '#eab308'
    };
    return colors[t] || '#6366f1';
  }
}
