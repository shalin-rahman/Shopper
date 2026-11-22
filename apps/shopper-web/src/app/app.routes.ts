import { Routes } from '@angular/router';

import { AdminTenantsComponent } from './features/admin/admin-tenants.component';
import { HomeComponent } from './features/home/home.component';
import { ProductsPageComponent } from './features/products/products-page.component';
import { AccountingPageComponent } from './features/accounting/accounting-page.component';
import { SuppliersPageComponent } from './features/suppliers/suppliers-page.component';
import { ExpensesPageComponent } from './features/expenses/expenses-page.component';
import { CustomersPageComponent } from './features/customers/customers-page.component';
import { StaffPageComponent } from './features/staff/staff-page.component';

import { ProcurementPageComponent } from './features/procurement/procurement-page.component';
import { InvoicesPageComponent } from './features/invoices/invoices-page.component';
import { InventoryPageComponent } from './features/inventory/inventory-page.component';
import { PaymentsPageComponent } from './features/payments/payments-page.component';
import { SettingsPageComponent } from './features/settings/settings-page.component';
import { LoginPageComponent } from './features/login/login-page.component';
import { CheckoutPageComponent } from './features/checkout/checkout-page.component';
import { CheckoutResultComponent } from './features/checkout/checkout-result.component';
import { authGuard } from './core/auth/auth.guard';
import { moduleGuard, roleGuard } from './core/nav/module.guard';

export const routes: Routes = [
  { path: 'login', component: LoginPageComponent },
  // Must stay above checkout/:id, or "result" is read as an invoice id.
  { path: 'checkout/result', component: CheckoutResultComponent },
  // Customers open this from a signed pay link; they have no staff login.
  { path: 'checkout/:id', component: CheckoutPageComponent },
  // Platform admin uses its own API key, not a staff login.
  { path: 'admin/tenants', component: AdminTenantsComponent },
  {
    path: '',
    canActivateChild: [authGuard],
    children: [
      { path: '', component: HomeComponent },
      { path: 'products', component: ProductsPageComponent },
      { path: 'invoices', component: InvoicesPageComponent },
      { path: 'inventory', component: InventoryPageComponent, canActivate: [moduleGuard('inventory')] },
      { path: 'payments', component: PaymentsPageComponent, canActivate: [roleGuard(['manager', 'admin'])] },
      { path: 'procurement', component: ProcurementPageComponent, canActivate: [moduleGuard('procurement')] },
      { path: 'suppliers', component: SuppliersPageComponent, canActivate: [moduleGuard('procurement')] },
      { path: 'expenses', component: ExpensesPageComponent, canActivate: [moduleGuard('expenses')] },
      { path: 'accounting', component: AccountingPageComponent, canActivate: [moduleGuard('accounting')] },
      { path: 'customers', component: CustomersPageComponent, canActivate: [moduleGuard('customers')] },
      { path: 'staff', component: StaffPageComponent },
      { path: 'settings', component: SettingsPageComponent, canActivate: [roleGuard(['manager', 'admin'])] },
    ],
  },
];
