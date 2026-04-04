import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Product {
  id: string;
  tenant_id: string;
  category_id: string | null;
  sku: string;
  name_en: string;
  name_bn: string;
  description_en: string | null;
  description_bn: string | null;
  unit: string;
  buy_price: string | null;
  sell_price: string | null;
  mrp: string | null;
  vat_rate_pct: string;
  barcode: string | null;
  qr_payload: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductCreateBody {
  sku: string;
  name_en: string;
  name_bn: string;
  unit?: string;
  sell_price?: number | null;
  vat_rate_pct?: number;
}

@Injectable({ providedIn: 'root' })
export class ProductService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  list(): Observable<Product[]> {
    return this.http.get<Product[]>(`${this.base}/v1/tenant/products`);
  }

  create(body: ProductCreateBody): Observable<Product> {
    return this.http.post<Product>(`${this.base}/v1/tenant/products`, body);
  }

  deactivate(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/v1/tenant/products/${id}`);
  }
}
