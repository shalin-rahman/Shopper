import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideTransloco } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { ShopperTranslocoHttpLoader } from '../../core/i18n/transloco-loader';
import { TenantSettingsDto, TenantSettingsService } from '../../core/tenant/tenant-settings.service';
import { ThemeService } from '../../core/theme/theme.service';
import { SettingsPageComponent } from './settings-page.component';

function settings(over: Partial<TenantSettingsDto> = {}): TenantSettingsDto {
  return {
    tenant_id: 't1',
    theme_id: 'default',
    default_language: 'en',
    logo_url: null,
    legal_title_en: 'Acme Ltd',
    legal_title_bn: null,
    bin: '123',
    default_vat_rate_pct: '15.00',
    module_access: { pos: true, inventory: false },
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-01T00:00:00Z',
    ...over,
  };
}

describe('SettingsPageComponent', () => {
  let api: jasmine.SpyObj<TenantSettingsService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<TenantSettingsService>('TenantSettingsService', ['load', 'update']);
    api.load.and.returnValue(of(settings()));
    await TestBed.configureTestingModule({
      imports: [SettingsPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideTransloco({
          config: { availableLangs: ['en', 'bn'], defaultLang: 'en', prodMode: true },
          loader: ShopperTranslocoHttpLoader,
        }),
        { provide: TenantSettingsService, useValue: api },
      ],
    }).compileComponents();
  });

  afterEach(() => {
    document.documentElement.removeAttribute('data-theme');
    localStorage.removeItem('shopper_web_theme');
  });

  function create() {
    const fixture = TestBed.createComponent(SettingsPageComponent);
    fixture.detectChanges();
    return fixture.componentInstance;
  }

  it('fills the form from the API and lists modules', () => {
    const page = create();
    expect(page.form?.default_vat_rate_pct).toBe(15);
    expect(page.form?.logo_url).toBe('');
    expect(page.moduleKeys()).toEqual(['inventory', 'pos']);
  });

  it('does not call the API when nothing changed', () => {
    const page = create();
    page.save();
    expect(api.update).not.toHaveBeenCalled();
    expect(page.message()).toEqual({ key: 'settings.noChanges', error: false });
  });

  it('sends only changed fields, and empty text as null', () => {
    api.update.and.returnValue(of(settings({ theme_id: 'ruby', bin: null })));
    const page = create();
    page.form!.theme_id = 'ruby';
    page.form!.bin = '   ';
    page.form!.module_access['inventory'] = true;
    page.save();

    expect(api.update).toHaveBeenCalledWith({
      theme_id: 'ruby',
      bin: null,
      module_access: { pos: true, inventory: true },
    });
    expect(page.message()).toEqual({ key: 'settings.saved', error: false });
    expect(document.documentElement.getAttribute('data-theme')).toBe('ruby');
    expect(TestBed.inject(ThemeService).currentTheme()).toBe('ruby');
    expect(localStorage.getItem('shopper_web_theme')).toBe('ruby');
    expect(page.saving()).toBeFalse();
  });

  it('rejects a VAT rate outside 0 to 100', () => {
    const page = create();
    page.form!.default_vat_rate_pct = 101;
    page.save();
    expect(api.update).not.toHaveBeenCalled();
    expect(page.message()?.key).toBe('settings.vatRange');
  });

  it('shows the API reason when the save is refused', () => {
    api.update.and.returnValue(
      throwError(() => new HttpErrorResponse({ status: 422, error: { detail: 'These settings cannot be empty: theme_id' } })),
    );
    const page = create();
    page.form!.default_language = 'bn';
    page.save();
    expect(page.message()?.text).toBe('These settings cannot be empty: theme_id');
    expect(page.saving()).toBeFalse();
  });

  it('counts unsaved changes and discards them', () => {
    const page = create();
    expect(page.dirtyCount()).toBe(0);
    page.form!.bin = '999';
    page.form!.module_access['pos'] = false;
    expect(page.dirtyCount()).toBe(2);

    page.discard();
    expect(page.dirtyCount()).toBe(0);
    expect(page.form!.bin).toBe('123');
    expect(page.form!.module_access).toEqual({ pos: true, inventory: false });
  });

  it('counts a cleared VAT field so save can report it', () => {
    const page = create();
    page.form!.default_vat_rate_pct = null;
    expect(page.dirtyCount()).toBe(1);
    page.save();
    expect(page.message()?.key).toBe('settings.vatRange');
  });

  it('picks the receipt name by the same rule as the server', () => {
    const page = create();
    expect(page.receiptTitle()).toBe('Acme Ltd');

    page.form!.default_language = 'bn';
    expect(page.receiptTitle()).toBe('Acme Ltd');
    page.form!.legal_title_bn = ' একমি লিমিটেড ';
    expect(page.receiptTitle()).toBe('একমি লিমিটেড');

    page.form!.default_language = 'en';
    page.form!.legal_title_en = '  ';
    expect(page.receiptTitle()).toBe('');
  });

  it('names known modules and leaves unknown ones as keys', () => {
    const page = create();
    expect(page.moduleLabel('pos')).toBe('settings.moduleNames.pos');
    expect(page.moduleLabel('loyalty')).toBeNull();
  });

  it('shows the load error when settings cannot be read', () => {
    api.load.and.returnValue(throwError(() => new Error('403')));
    const page = create();
    expect(page.message()?.key).toBe('settings.loadFailed');
    expect(page.loaded()).toBeFalse();
  });
});
