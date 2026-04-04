import { catchError, firstValueFrom, of } from 'rxjs';

import { LocaleService, ShopperLang } from '../i18n/locale.service';
import { TenantSettingsService } from './tenant-settings.service';

/**
 * After Transloco locale hydrate: apply server `default_language` only if user has no saved preference;
 * set `data-theme` for CSS variable–based storefront/admin theming.
 */
export function createTenantBootstrapInitializer(
  locale: LocaleService,
  tenantSettings: TenantSettingsService,
) {
  return () =>
    firstValueFrom(
      tenantSettings.load().pipe(
        catchError(() => of(null)),
      ),
    ).then((s) => {
      if (!s) {
        return;
      }
      document.documentElement.setAttribute('data-theme', s.theme_id);
      if (localStorage.getItem('shopper.lang')) {
        return;
      }
      const lang = s.default_language;
      if (lang === 'en' || lang === 'bn') {
        locale.setLanguage(lang as ShopperLang, { persist: false });
      }
    });
}
