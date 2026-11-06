import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideTransloco } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { ShopperTranslocoHttpLoader } from '../../core/i18n/transloco-loader';
import { PaymentReview, PaymentReviewService } from './payment-review.service';
import { PaymentsPageComponent } from './payments-page.component';

function review(id: string): PaymentReview {
  return {
    id,
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
}

describe('PaymentsPageComponent', () => {
  let api: jasmine.SpyObj<PaymentReviewService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<PaymentReviewService>('PaymentReviewService', ['listOpen', 'resolve', 'refund']);
    api.listOpen.and.returnValue(of([review('a'), review('b')]));
    await TestBed.configureTestingModule({
      imports: [PaymentsPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideTransloco({
          config: { availableLangs: ['en', 'bn'], defaultLang: 'en', prodMode: true },
          loader: ShopperTranslocoHttpLoader,
        }),
        { provide: PaymentReviewService, useValue: api },
      ],
    }).compileComponents();
  });

  function create() {
    const fixture = TestBed.createComponent(PaymentsPageComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('shows one row per open review', () => {
    const fixture = create();
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(2);
  });

  it('will not resolve without a note', () => {
    const page = create().componentInstance;
    page.notes['a'] = '   ';
    page.resolve(page.reviews()[0]);

    expect(api.resolve).not.toHaveBeenCalled();
    expect(page.rowError()).toEqual({ id: 'a', key: 'payments.noteRequired' });
  });

  it('drops the row once resolved', () => {
    api.resolve.and.returnValue(of({ ...review('a'), review_resolved_at: '2026-10-23T11:00:00Z' }));
    const page = create().componentInstance;
    page.notes['a'] = 'Refunded at gateway';
    page.resolve(page.reviews()[0]);

    expect(api.resolve).toHaveBeenCalledWith('a', 'Refunded at gateway');
    expect(page.reviews().map((r) => r.id)).toEqual(['b']);
    expect(page.resolving()).toBeNull();
  });

  it('keeps the row and shows an error when resolve fails', () => {
    api.resolve.and.returnValue(throwError(() => new Error('404')));
    const page = create().componentInstance;
    page.notes['a'] = 'Refunded';
    page.resolve(page.reviews()[0]);

    expect(page.reviews().length).toBe(2);
    expect(page.rowError()).toEqual({ id: 'a', key: 'payments.resolveFailed' });
    expect(page.resolving()).toBeNull();
  });

  it('shows the load error when the list fails', () => {
    api.listOpen.and.returnValue(throwError(() => new Error('403')));
    const page = create().componentInstance;
    expect(page.loadError()).toBe('payments.loadFailed');
    expect(page.loaded()).toBeFalse();
  });

  it('will not refund without an amount above zero', () => {
    const page = create().componentInstance;
    page.refundAmounts['a'] = 0;
    page.refund(page.reviews()[0]);

    expect(api.refund).not.toHaveBeenCalled();
    expect(page.refundMsg()).toEqual({ id: 'a', key: 'payments.refundAmountRequired', error: true });
  });

  it('records a refund and keeps the row for the resolve step', () => {
    api.refund.and.returnValue(of({}));
    const page = create().componentInstance;
    page.refundAmounts['a'] = 120.5;
    page.notes['a'] = 'bKash ref 77';
    page.refund(page.reviews()[0]);

    expect(api.refund).toHaveBeenCalledWith('a', 120.5, 'bKash ref 77');
    expect(page.refundMsg()).toEqual({ id: 'a', key: 'payments.refunded', error: false });
    expect(page.reviews().length).toBe(2);
  });

  it('shows the API reason when the refund is refused', () => {
    api.refund.and.returnValue(
      throwError(() => new HttpErrorResponse({ status: 409, error: { detail: 'Refund exceeds the payment amount' } })),
    );
    const page = create().componentInstance;
    page.refundAmounts['a'] = 9999;
    page.refund(page.reviews()[0]);

    expect(page.refundMsg()?.text).toBe('Refund exceeds the payment amount');
    expect(page.resolving()).toBeNull();
  });
});
