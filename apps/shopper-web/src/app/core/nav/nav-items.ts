export type StaffRole = 'cashier' | 'accountant' | 'manager' | 'admin';

/** Modules a shop can switch off. `pos` has no web page; it is the mobile app. */
export const MODULE_KEYS = ['inventory', 'procurement', 'expenses', 'accounting', 'customers', 'pos'] as const;
export type ModuleKey = (typeof MODULE_KEYS)[number];

export function isModuleKey(key: string): key is ModuleKey {
  return (MODULE_KEYS as readonly string[]).includes(key);
}

export interface NavItem {
  path: string;
  label: string;
  /** Left out means every role. */
  roles?: StaffRole[];
  module?: ModuleKey;
  exact?: boolean;
}

// Roles follow the API: payments review and settings edit need a manager.
export const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'nav.home', exact: true },
  { path: '/products', label: 'nav.products' },
  { path: '/invoices', label: 'nav.invoices' },
  { path: '/inventory', label: 'nav.inventory', module: 'inventory' },
  { path: '/procurement', label: 'nav.procurement', module: 'procurement' },
  { path: '/suppliers', label: 'nav.suppliers', module: 'procurement' },
  { path: '/expenses', label: 'nav.expenses', module: 'expenses' },
  { path: '/payments', label: 'nav.payments', roles: ['manager', 'admin'] },
  { path: '/accounting', label: 'nav.accounting', module: 'accounting' },
  { path: '/customers', label: 'nav.customers', module: 'customers' },
  { path: '/staff', label: 'nav.staff' },
  { path: '/settings', label: 'nav.settings', roles: ['manager', 'admin'] },
];

export function visibleNav(role: string | null, moduleOn: (key: string) => boolean): NavItem[] {
  return NAV_ITEMS.filter(
    (item) =>
      (!item.roles || (role !== null && (item.roles as string[]).includes(role))) &&
      (!item.module || moduleOn(item.module)),
  );
}
