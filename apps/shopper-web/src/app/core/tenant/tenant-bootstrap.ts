import { AuthService } from '../auth/auth.service';
import { TenantSettingsStore } from './tenant-settings.store';

/** Load the shop's settings at start only when someone is signed in; login loads them otherwise. */
export function createTenantBootstrapInitializer(auth: AuthService, store: TenantSettingsStore) {
  return (): Promise<void> => (auth.isLoggedIn() ? store.load() : Promise.resolve());
}
