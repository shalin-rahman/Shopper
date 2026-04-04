import { Routes } from '@angular/router';

import { HomeComponent } from './features/home/home.component';
import { ProductsPageComponent } from './features/products/products-page.component';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'products', component: ProductsPageComponent },
];
