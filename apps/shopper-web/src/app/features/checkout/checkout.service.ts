import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

export type CheckoutGateway = 'bkash' | 'nagad' | 'sslcommerz';

export interface CheckoutInvoice {
  id: string;
  invoice_no: string;
  total_amount: string | number;
  amount_paid: string | number;
  balance_due: string | number;
  status: string;
  lines: { id: string; description: string; qty: string | number; line_total: string | number }[];
}

export interface CheckoutLinkParams {
  t: string;
  e: string;
}

@Injectable({ providedIn: 'root' })
export class CheckoutService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/v1/storefront/checkout`;

  load(invoiceId: string, link: CheckoutLinkParams): Observable<CheckoutInvoice> {
    return this.http.get<CheckoutInvoice>(`${this.base}/${invoiceId}`, { params: { ...link } });
  }

  pay(
    invoiceId: string,
    link: CheckoutLinkParams,
    gateway: CheckoutGateway,
    amount: string | number,
  ): Observable<{ gateway_url: string | null }> {
    return this.http.post<{ gateway_url: string | null }>(
      `${this.base}/${invoiceId}/pay`,
      { gateway, amount: String(amount), invoice_id: invoiceId },
      { params: { ...link } },
    );
  }
}
