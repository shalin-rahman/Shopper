import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { AuthService } from '../auth/auth.service';
import { LocaleService } from '../i18n/locale.service';
import { ThemeService } from '../theme/theme.service';
import { createTenantBootstrapInitializer } from './tenant-bootstrap';
import { TenantSettingsDto, TenantSettingsService } from './tenant-settings.service';
import { TenantSettingsStore } from './tenant-settings.store';

function settings(over: Partial<TenantSettingsDto> = {}): TenantSettingsDto {
  return {
    tenant_id: 't1',
    theme_id: 'emerald',
    default_language: 'bn',
    logo_url: null,
    legal_title_en: null,
    legal_title_bn: null,
    bin: null,
    default_vat_rate_pct: '15',
    module_access: {},
    created_at: '',
    updated_at: '',
    ...over,
  };
}

describe('TenantSettingsStore', () => {
  let api: jasmine.SpyObj<TenantSettingsService>;
  let locale: jasmine.SpyObj<LocaleService>;
  let store: TenantSettingsStore;
  let theme: ThemeService;

  beforeEach(() => {
    localStorage.removeItem('shopper_web_theme');
    localStorage.removeItem('shopper.lang');
    api = jasmine.createSpyObj<TenantSettingsService>('TenantSettingsService', ['load']);
    locale = jasmine.createSpyObj<LocaleService>('LocaleService', ['setLanguage']);
    TestBed.configureTestingModule({
      providers: [
        { provide: TenantSettingsService, useValue: api },
        { provide: LocaleService, useValue: locale },
      ],
    });
    store = TestBed.inject(TenantSettingsStore);
    theme = TestBed.inject(ThemeService);
  });

  afterEach(() => {
    localStorage.removeItem('shopper_web_theme');
    localStorage.removeItem('shopper.lang');
    document.documentElement.removeAttribute('data-theme');
  });

  it('applies the shop theme and language when the user saved neither', async () => {
    api.load.and.returnValue(of(settings()));
    await store.load();
    expect(store.settings()?.theme_id).toBe('emerald');
    expect(theme.currentTheme()).toBe('emerald');
    expect(document.documentElement.getAttribute('data-theme')).toBe('emerald');
    expect(localStorage.getItem('shopper_web_theme')).toBeNull();
    expect(locale.setLanguage).toHaveBeenCalledWith('bn', { persist: false });
  });

  it("keeps the user's saved theme and language", async () => {
    theme.setTheme('ruby');
    localStorage.setItem('shopper.lang', 'en');
    api.load.and.returnValue(of(settings()));
    await store.load();
    expect(theme.currentTheme()).toBe('ruby');
    expect(locale.setLanguage).not.toHaveBeenCalled();
  });

  it('skips an unknown shop theme', async () => {
    api.load.and.returnValue(of(settings({ theme_id: 'neon', default_language: 'fr' })));
    await store.load();
    expect(theme.currentTheme()).toBe('default');
    expect(locale.setLanguage).not.toHaveBeenCalled();
  });

  it('applies nothing when the load fails', async () => {
    api.load.and.returnValue(throwError(() => new Error('403')));
    await store.load();
    expect(store.settings()).toBeNull();
    expect(theme.currentTheme()).toBe('default');
    expect(locale.setLanguage).not.toHaveBeenCalled();
  });

  it('treats a missing module key as on', async () => {
    expect(store.moduleOn('inventory')).toBeTrue();
    api.load.and.returnValue(of(settings({ module_access: { inventory: false, pos: true } })));
    await store.load();
    expect(store.moduleOn('inventory')).toBeFalse();
    expect(store.moduleOn('pos')).toBeTrue();
    expect(store.moduleOn('expenses')).toBeTrue();
  });

  it('clear drops the settings', async () => {
    api.load.and.returnValue(of(settings()));
    await store.load();
    store.clear();
    expect(store.settings()).toBeNull();
  });
});

describe('createTenantBootstrapInitializer', () => {
  it('does not call the API when logged out', async () => {
    const auth = jasmine.createSpyObj<AuthService>('AuthService', ['isLoggedIn']);
    const store = jasmine.createSpyObj<TenantSettingsStore>('TenantSettingsStore', ['load']);
    auth.isLoggedIn.and.returnValue(false);
    await createTenantBootstrapInitializer(auth, store)();
    expect(store.load).not.toHaveBeenCalled();
  });

  it('loads settings when logged in', async () => {
    const auth = jasmine.createSpyObj<AuthService>('AuthService', ['isLoggedIn']);
    const store = jasmine.createSpyObj<TenantSettingsStore>('TenantSettingsStore', ['load']);
    auth.isLoggedIn.and.returnValue(true);
    store.load.and.resolveTo();
    await createTenantBootstrapInitializer(auth, store)();
    expect(store.load).toHaveBeenCalled();
  });
});
