import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../auth/auth.service';
import { TenantSettingsStore } from '../tenant/tenant-settings.store';
import { ModuleKey, StaffRole } from './nav-items';

/** Allows the page while settings are not loaded, so a slow API never locks it (D3). */
export function moduleGuard(key: ModuleKey): CanActivateFn {
  return () => inject(TenantSettingsStore).moduleOn(key) || inject(Router).createUrlTree(['/']);
}

/** Hides pages the API would refuse anyway; the API still checks the role. */
export function roleGuard(roles: StaffRole[]): CanActivateFn {
  return () => {
    const role = inject(AuthService).role();
    return (role !== null && (roles as string[]).includes(role)) || inject(Router).createUrlTree(['/']);
  };
}
