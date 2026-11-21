import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';

import { CheckoutResultComponent } from './checkout-result.component';

const en = {
  checkout: {
    result: {
      success: 'Paid OK',
      fail: 'Not paid',
      cancel: 'Cancelled',
      unknown: 'No result',
      pending: 'Shop will see it',
    },
  },
};

describe('CheckoutResultComponent', () => {
  function render(query: Record<string, string>): string {
    TestBed.configureTestingModule({
      imports: [
        CheckoutResultComponent,
        TranslocoTestingModule.forRoot({
          langs: { en },
          translocoConfig: { availableLangs: ['en'], defaultLang: 'en' },
          preloadLangs: true,
        }),
      ],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    const fixture = TestBed.createComponent(CheckoutResultComponent);
    fixture.detectChanges();
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  it('shows the success text and the pending line for status=success', () => {
    const text = render({ status: 'success' });
    expect(text).toContain('Paid OK');
    expect(text).toContain('Shop will see it');
  });

  it('shows the cancel text for status=cancel', () => {
    expect(render({ status: 'cancel' })).toContain('Cancelled');
  });

  it('shows the unknown text for any other status', () => {
    const text = render({ status: 'x' });
    expect(text).toContain('No result');
    expect(text).not.toContain('Shop will see it');
  });

  it('shows the unknown text when status is missing', () => {
    expect(render({})).toContain('No result');
  });
});
