import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { Product, ProductService, filterProducts } from './product.service';

function product(overrides: Partial<Product>): Product {
  return {
    id: 'p1',
    tenant_id: 't1',
    category_id: null,
    sku: 'PROD-001',
    name_en: 'Smart Watch',
    name_bn: 'স্মার্ট ওয়াচ',
    description_en: null,
    description_bn: null,
    unit: 'pcs',
    buy_price: null,
    sell_price: '3200',
    mrp: null,
    vat_rate_pct: '5',
    barcode: null,
    qr_payload: null,
    is_active: true,
    marketplace_enabled: false,
    stock_quantity: '20',
    created_at: '',
    updated_at: '',
    ...overrides,
  };
}

describe('filterProducts', () => {
  const watch = product({ id: 'a', sku: 'PROD-001', name_en: 'Smart Watch', barcode: '8901234' });
  const rice = product({ id: 'b', sku: 'PROD-002', name_en: 'Basmati Rice', name_bn: 'বাসমতি চাল' });
  const all = [watch, rice];

  it('returns every product for a blank query', () => {
    expect(filterProducts(all, '')).toEqual(all);
    expect(filterProducts(all, '   ')).toEqual(all);
  });

  it('matches sku and English name without regard to case', () => {
    expect(filterProducts(all, 'prod-002')).toEqual([rice]);
    expect(filterProducts(all, 'WATCH')).toEqual([watch]);
  });

  it('matches the Bangla name and the barcode', () => {
    expect(filterProducts(all, 'চাল')).toEqual([rice]);
    expect(filterProducts(all, '8901')).toEqual([watch]);
  });

  it('returns nothing when no product matches', () => {
    expect(filterProducts(all, 'laptop')).toEqual([]);
  });
});

describe('ProductService', () => {
  let service: ProductService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ProductService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('setMarketplace sends a PATCH with only the marketplace flag', () => {
    let result: Product | undefined;
    service.setMarketplace('p1', true).subscribe((p) => (result = p));

    const req = http.expectOne('/api/v1/tenant/products/p1');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ marketplace_enabled: true });
    req.flush(product({ marketplace_enabled: true }));

    expect(result?.marketplace_enabled).toBeTrue();
  });
});
