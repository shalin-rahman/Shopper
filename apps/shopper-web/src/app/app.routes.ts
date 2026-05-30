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

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'products', component: ProductsPageComponent },
  { path: 'invoices', component: InvoicesPageComponent },
  { path: 'inventory', component: InventoryPageComponent },
  { path: 'procurement', component: ProcurementPageComponent },
  { path: 'suppliers', component: SuppliersPageComponent },
  { path: 'expenses', component: ExpensesPageComponent },
  { path: 'accounting', component: AccountingPageComponent },
  { path: 'customers', component: CustomersPageComponent },
  { path: 'staff', component: StaffPageComponent },
  { path: 'admin/tenants', component: AdminTenantsComponent },
];
