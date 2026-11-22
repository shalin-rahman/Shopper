import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { LocaleService } from '../i18n/locale.service';
import { ThemeService, isShopperTheme } from '../theme/theme.service';
import { TenantSettingsDto, TenantSettingsService } from './tenant-settings.service';

const LANG_KEY = 'shopper.lang';

function hasSavedLang(): boolean {
  try {
    return !!localStorage.getItem(LANG_KEY);
  } catch {
    return false;
  }
}

/** The shop's settings for the signed-in user. Null until loaded or when the load fails. */
@Injectable({ providedIn: 'root' })
export class TenantSettingsStore {
  private readonly api = inject(TenantSettingsService);
  private readonly theme = inject(ThemeService);
  private readonly locale = inject(LocaleService);

  readonly settings = signal<TenantSettingsDto | null>(null);

  /** Never rejects. The user's own saved theme and language win over the shop's (D4). */
  async load(): Promise<void> {
    let s: TenantSettingsDto;
    try {
      s = await firstValueFrom(this.api.load());
    } catch {
      return;
    }
    this.settings.set(s);
    if (!this.theme.hasSavedTheme() && isShopperTheme(s.theme_id)) {
      this.theme.setTheme(s.theme_id, { persist: false });
    }
    const lang = s.default_language;
    if (!hasSavedLang() && (lang === 'en' || lang === 'bn')) {
      this.locale.setLanguage(lang, { persist: false });
    }
  }

  clear(): void {
    this.settings.set(null);
  }

  /** A missing key means the module is on (D3). */
  moduleOn(key: string): boolean {
    return this.settings()?.module_access?.[key] !== false;
  }
}
