import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
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

  private activeLinkWatch?: ResizeObserver;

  constructor() {
    // On a phone the nav row scrolls sideways; keep the current page's link in view.
    // Link widths change when translations load, so it re-centres on each resize.
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd), takeUntilDestroyed())
      .subscribe(() => setTimeout(() => this.watchActiveLink()));
    inject(DestroyRef).onDestroy(() => this.activeLinkWatch?.disconnect());
  }

  private watchActiveLink(): void {
    this.activeLinkWatch?.disconnect();
    const link = document.querySelector<HTMLElement>('.app-nav .is-active');
    const nav = link?.parentElement;
    if (!link || !nav || typeof ResizeObserver === 'undefined') return;
    this.activeLinkWatch = new ResizeObserver(() => {
      nav.scrollLeft = link.offsetLeft - nav.offsetLeft - (nav.clientWidth - link.offsetWidth) / 2;
    });
    this.activeLinkWatch.observe(link);
  }
}
