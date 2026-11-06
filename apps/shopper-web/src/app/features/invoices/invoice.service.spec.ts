import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { InvoiceService, invoiceActions } from './invoice.service';

describe('InvoiceService', () => {
  let svc: InvoiceService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    svc = TestBed.inject(InvoiceService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('posts issue, cancel and checkout-link to the invoice', () => {
    svc.issue('a1').subscribe();
    svc.cancel('a1').subscribe();
    svc.checkoutLink('a1').subscribe();
    for (const action of ['issue', 'cancel', 'checkout-link']) {
      const req = http.expectOne(`/api/v1/tenant/invoices/a1/${action}`);
      expect(req.request.method).toBe('POST');
      req.flush({});
    }
  });

  it('lists invoices', () => {
    svc.list().subscribe((rows) => expect(rows.length).toBe(1));
    http.expectOne('/api/v1/tenant/invoices').flush([{ id: 'a1' }]);
  });
});

describe('invoiceActions', () => {
  it('offers issue and cancel on a draft, no pay link', () => {
    expect(invoiceActions('draft')).toEqual({ issue: true, cancel: true, payLink: false });
  });

  it('offers cancel and pay link on an issued invoice', () => {
    expect(invoiceActions('issued')).toEqual({ issue: false, cancel: true, payLink: true });
  });

  it('offers only a pay link when partly paid', () => {
    expect(invoiceActions('partially_paid')).toEqual({ issue: false, cancel: false, payLink: true });
  });

  it('offers nothing on paid or cancelled', () => {
    const none = { issue: false, cancel: false, payLink: false };
    expect(invoiceActions('paid')).toEqual(none);
    expect(invoiceActions('cancelled')).toEqual(none);
  });
});
