import { Routes } from '@angular/router';

import { AdminTenantsComponent } from './features/admin/admin-tenants.component';
import { HomeComponent } from './features/home/home.component';
import { ProductsPageComponent } from './features/products/products-page.component';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'products', component: ProductsPageComponent },
  { path: 'admin/tenants', component: AdminTenantsComponent },
];
