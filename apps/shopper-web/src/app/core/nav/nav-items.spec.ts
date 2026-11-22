import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideTransloco } from '@ngneat/transloco';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';

import { AuthService } from '../auth/auth.service';
import { TenantSettingsDto } from '../tenant/tenant-settings.service';
import { TenantSettingsStore } from '../tenant/tenant-settings.store';
import { moduleGuard, roleGuard } from './module.guard';
import { visibleNav } from './nav-items';

const allOn = () => true;
const paths = (role: string | null, moduleOn: (k: string) => boolean = allOn) =>
  visibleNav(role, moduleOn).map((i) => i.path);

describe('visibleNav', () => {
  it('hides payments and settings from a cashier', () => {
    const p = paths('cashier');
    expect(p).not.toContain('/payments');
    expect(p).not.toContain('/settings');
    expect(p).toContain('/products');
  });

  it('shows payments and settings to a manager and an admin', () => {
    for (const role of ['manager', 'admin']) {
      expect(paths(role)).toContain('/payments');
      expect(paths(role)).toContain('/settings');
    }
  });

  it('hides links whose module is off', () => {
    const p = paths('admin', (k) => k !== 'inventory');
    expect(p).not.toContain('/inventory');
    expect(p).toContain('/procurement');
  });

  it('hides both purchasing links when procurement is off', () => {
    const p = paths('admin', (k) => k !== 'procurement');
    expect(p).not.toContain('/procurement');
    expect(p).not.toContain('/suppliers');
  });

  it('never shows the platform admin link', () => {
    expect(paths('admin').some((p) => p.startsWith('/admin'))).toBeFalse();
  });

  it('shows only links open to every role when the role is unknown', () => {
    const p = paths(null);
    expect(p).toContain('/');
    expect(p).not.toContain('/settings');
  });
});

describe('moduleGuard and roleGuard', () => {
  let role: string | null;
  const route = {} as ActivatedRouteSnapshot;
  const state = { url: '/x' } as RouterStateSnapshot;

  beforeEach(() => {
    role = 'cashier';
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideTransloco({ config: { availableLangs: ['en', 'bn'], defaultLang: 'en', prodMode: true } }),
        { provide: AuthService, useValue: { role: () => role } },
      ],
    });
  });

  function setModules(module_access: Record<string, unknown>): void {
    TestBed.inject(TenantSettingsStore).settings.set({ module_access } as TenantSettingsDto);
  }

  const run = (guard: ReturnType<typeof moduleGuard>) =>
    TestBed.runInInjectionContext(() => guard(route, state));
  const home = () => TestBed.inject(Router).serializeUrl(TestBed.inject(Router).createUrlTree(['/']));

  it('redirects home when the module is off', () => {
    setModules({ inventory: false });
    const result = run(moduleGuard('inventory'));
    expect(result instanceof UrlTree).toBeTrue();
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe(home());
  });

  it('allows the route when the key is missing or settings are not loaded', () => {
    setModules({});
    expect(run(moduleGuard('inventory'))).toBeTrue();
    TestBed.inject(TenantSettingsStore).clear();
    expect(run(moduleGuard('inventory'))).toBeTrue();
  });

  it('redirects a cashier away from a manager page and lets a manager in', () => {
    expect(run(roleGuard(['manager', 'admin'])) instanceof UrlTree).toBeTrue();
    role = 'manager';
    expect(run(roleGuard(['manager', 'admin']))).toBeTrue();
  });
});
