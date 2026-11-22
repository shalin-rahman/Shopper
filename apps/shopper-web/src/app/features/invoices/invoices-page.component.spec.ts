import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { InvoiceRow, InvoiceService } from './invoice.service';
import { InvoicesPageComponent } from './invoices-page.component';

const draft: InvoiceRow = {
  id: 'a1', invoice_no: 'INV-1', total_amount: 100, amount_paid: 0, balance_due: 100,
  status: 'draft', created_at: '2026-10-23',
};

describe('InvoicesPageComponent', () => {
  let api: jasmine.SpyObj<InvoiceService>;

  function make() {
    api = jasmine.createSpyObj<InvoiceService>('InvoiceService', ['list', 'issue', 'cancel', 'checkoutLink']);
    api.list.and.returnValue(of([draft]));
    TestBed.configureTestingModule({
      imports: [InvoicesPageComponent, TranslocoTestingModule.forRoot({
        langs: { en: { invoices: { requestFailed: 'Try again' } } },
        preloadLangs: true,
        translocoConfig: { availableLangs: ['en'], defaultLang: 'en' },
      })],
      providers: [{ provide: InvoiceService, useValue: api }],
    });
    const page = TestBed.createComponent(InvoicesPageComponent).componentInstance;
    page.ngOnInit();
    return page;
  }

  it('replaces the row after a successful issue', () => {
    const page = make();
    api.issue.and.returnValue(of({ ...draft, status: 'issued' }));
    page.issue(draft);
    expect(page.invoices()[0].status).toBe('issued');
    expect(page.busyId()).toBeNull();
  });

  it('shows the API reason on the row when issue is refused', () => {
    const page = make();
    api.issue.and.returnValue(
      throwError(() => new HttpErrorResponse({ status: 409, error: { detail: 'Not enough stock for SKU A' } })),
    );
    page.issue(draft);
    expect(page.rowMessage()['a1']).toEqual({ text: 'Not enough stock for SKU A', error: true });
    expect(page.invoices()[0].status).toBe('draft');
  });

  it('shows a translated fallback when the API sends no reason', () => {
    const page = make();
    api.issue.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));
    page.issue(draft);
    expect(page.rowMessage()['a1']).toEqual({ text: 'Try again', error: true });
  });

  it('does not cancel when the user says no', () => {
    const page = make();
    spyOn(window, 'confirm').and.returnValue(false);
    page.cancel(draft);
    expect(api.cancel).not.toHaveBeenCalled();
  });

  it('shows the full pay link on the row', () => {
    const page = make();
    api.checkoutLink.and.returnValue(of({ invoice_id: 'a1', token: 't', expires: 9, path: '/checkout/a1?t=t&e=9' }));
    page.payLink({ ...draft, status: 'issued' });
    expect(page.rowMessage()['a1'].text).toBe(`${window.location.origin}/checkout/a1?t=t&e=9`);
  });
});
