import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { CheckoutInvoice, CheckoutService } from './checkout.service';
import { CheckoutPageComponent, goToGateway } from './checkout-page.component';

const invoice: CheckoutInvoice = {
  id: 'a1', invoice_no: 'INV-1', total_amount: '100.00', amount_paid: '40.00', balance_due: '60.00',
  status: 'partially_paid', lines: [],
};

describe('CheckoutPageComponent', () => {
  let api: jasmine.SpyObj<CheckoutService>;

  function make(query: Record<string, string>) {
    api = jasmine.createSpyObj<CheckoutService>('CheckoutService', ['load', 'pay']);
    TestBed.configureTestingModule({
      imports: [CheckoutPageComponent, TranslocoTestingModule.forRoot({ langs: { en: {} } })],
      providers: [
        { provide: CheckoutService, useValue: api },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: 'a1' }), queryParamMap: convertToParamMap(query) } },
        },
      ],
    });
    return TestBed.createComponent(CheckoutPageComponent).componentInstance;
  }

  it('shows a bad link without calling the API when t or e is missing', () => {
    const page = make({ t: 'x' });
    page.ngOnInit();
    expect(page.state()).toBe('badLink');
    expect(api.load).not.toHaveBeenCalled();
  });

  it('shows a bad link when the API refuses the signature', () => {
    const page = make({ t: 'x', e: '9' });
    api.load.and.returnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
    page.ngOnInit();
    expect(page.state()).toBe('badLink');
  });

  it('pays the balance due and goes to the gateway page', () => {
    const page = make({ t: 'x', e: '9' });
    api.load.and.returnValue(of(invoice));
    api.pay.and.returnValue(of({ gateway_url: 'https://gw.example/pay/1' }));
    const open = spyOn(goToGateway, 'open');
    page.ngOnInit();
    page.gateway.set('bkash');
    page.pay();
    expect(api.pay).toHaveBeenCalledWith('a1', { t: 'x', e: '9' }, 'bkash', '60.00');
    expect(open).toHaveBeenCalledWith('https://gw.example/pay/1');
  });

  it('does not leave the app for a gateway URL that is not https', () => {
    const page = make({ t: 'x', e: '9' });
    api.load.and.returnValue(of(invoice));
    api.pay.and.returnValue(of({ gateway_url: 'javascript:alert(1)' }));
    const open = spyOn(goToGateway, 'open');
    page.ngOnInit();
    page.gateway.set('bkash');
    page.pay();
    expect(open).not.toHaveBeenCalled();
    expect(page.payError()).toBeTruthy();
    expect(page.paying()).toBeFalse();
  });

  it('shows the API reason when the payment cannot start', () => {
    const page = make({ t: 'x', e: '9' });
    api.load.and.returnValue(of(invoice));
    api.pay.and.returnValue(throwError(() => new HttpErrorResponse({ status: 409, error: { detail: 'Already paid' } })));
    page.ngOnInit();
    page.gateway.set('nagad');
    page.pay();
    expect(page.payError()).toEqual({ text: 'Already paid' });
    expect(page.paying()).toBeFalse();
  });

  it('offers no payment on a paid invoice', () => {
    const page = make({ t: 'x', e: '9' });
    api.load.and.returnValue(of({ ...invoice, status: 'paid', balance_due: '0.00' }));
    page.ngOnInit();
    expect(page.payable()).toBeFalse();
  });
});

describe('CheckoutService', () => {
  it('sends the link signature as query params on load and pay', () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    const svc = TestBed.inject(CheckoutService);
    const http = TestBed.inject(HttpTestingController);

    svc.load('a1', { t: 'tok', e: '9' }).subscribe();
    svc.pay('a1', { t: 'tok', e: '9' }, 'bkash', '60.00').subscribe();

    http.expectOne('/api/v1/storefront/checkout/a1?t=tok&e=9').flush({});
    const pay = http.expectOne('/api/v1/storefront/checkout/a1/pay?t=tok&e=9');
    expect(pay.request.body).toEqual({ gateway: 'bkash', amount: '60.00', invoice_id: 'a1' });
    pay.flush({});
    http.verify();
  });
});
