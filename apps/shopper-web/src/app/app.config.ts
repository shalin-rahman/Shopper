import { APP_INITIALIZER, ApplicationConfig, isDevMode } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { provideTransloco } from '@ngneat/transloco';

import { authInterceptor } from './core/auth/auth.interceptor';
import { AuthService } from './core/auth/auth.service';
import { shopperAdminInterceptor } from './core/http/shopper-admin.interceptor';
import { shopperTenantInterceptor } from './core/http/shopper-tenant.interceptor';
import { ShopperTranslocoHttpLoader } from './core/i18n/transloco-loader';
import { LocaleService } from './core/i18n/locale.service';
import { createTenantBootstrapInitializer } from './core/tenant/tenant-bootstrap';
import { TenantSettingsStore } from './core/tenant/tenant-settings.store';
import { routes } from './app.routes';

function initLocaleFactory(locale: LocaleService) {
  return () => {
    locale.hydrateFromStorage();
  };
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([shopperTenantInterceptor, shopperAdminInterceptor, authInterceptor])),
    provideRouter(routes),
    provideTransloco({
      config: {
        availableLangs: ['en', 'bn'],
        defaultLang: 'en',
        fallbackLang: 'en',
        reRenderOnLangChange: true,
        prodMode: !isDevMode(),
      },
      loader: ShopperTranslocoHttpLoader,
    }),
    {
      provide: APP_INITIALIZER,
      useFactory: initLocaleFactory,
      deps: [LocaleService],
      multi: true,
    },
    {
      provide: APP_INITIALIZER,
      useFactory: createTenantBootstrapInitializer,
      deps: [AuthService, TenantSettingsStore],
      multi: true,
    },
  ],
};
