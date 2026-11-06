import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { PaymentReview, PaymentReviewService } from './payment-review.service';

const review: PaymentReview = {
  id: 'pay1',
  gateway: 'sslcommerz',
  amount: '500.00',
  currency: 'BDT',
  status: 'completed',
  invoice_id: 'inv1',
  review_reason: 'overpayment',
  review_note: null,
  review_resolved_at: null,
  review_resolved_by: null,
  created_at: '2026-10-23T10:00:00Z',
  updated_at: '2026-10-23T10:00:00Z',
};

describe('PaymentReviewService', () => {
  let service: PaymentReviewService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(PaymentReviewService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists open reviews', () => {
    let rows: PaymentReview[] = [];
    service.listOpen().subscribe((r) => (rows = r));

    const req = http.expectOne('/api/v1/tenant/payments/review');
    expect(req.request.method).toBe('GET');
    req.flush([review]);

    expect(rows).toEqual([review]);
  });

  it('resolves a review with a trimmed note', () => {
    service.resolve('pay1', '  Refunded at gateway, ref 991  ').subscribe();

    const req = http.expectOne('/api/v1/tenant/payments/pay1/resolve-review');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ note: 'Refunded at gateway, ref 991' });
    req.flush({ ...review, review_resolved_at: '2026-10-23T11:00:00Z' });
  });

  it('posts a refund with two decimals and no blank note', () => {
    service.refund('pay1', 120.5, '   ').subscribe();

    const req = http.expectOne('/api/v1/tenant/payments/pay1/refunds');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ amount: '120.50', note: null });
    req.flush({});
  });
});
