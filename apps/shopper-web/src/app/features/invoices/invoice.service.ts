import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface InvoiceRow {
  id: string;
  invoice_no: string;
  customer_name?: string | null;
  total_amount: string | number;
  amount_paid: string | number;
  balance_due: string | number;
  status: string;
  created_at: string;
}

export interface CheckoutLink {
  invoice_id: string;
  token: string;
  expires: number;
  path: string;
}

@Injectable({ providedIn: 'root' })
export class InvoiceService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/v1/tenant/invoices`;

  list(): Observable<InvoiceRow[]> {
    return this.http.get<InvoiceRow[]>(this.base);
  }

  issue(id: string): Observable<InvoiceRow> {
    return this.http.post<InvoiceRow>(`${this.base}/${id}/issue`, {});
  }

  cancel(id: string): Observable<InvoiceRow> {
    return this.http.post<InvoiceRow>(`${this.base}/${id}/cancel`, {});
  }

  checkoutLink(id: string): Observable<CheckoutLink> {
    return this.http.post<CheckoutLink>(`${this.base}/${id}/checkout-link`, {});
  }
}

/** Which actions a row offers. Mirrors the API's own status rules. */
export function invoiceActions(status: string): { issue: boolean; cancel: boolean; payLink: boolean } {
  return {
    issue: status === 'draft',
    cancel: status === 'draft' || status === 'issued',
    payLink: status === 'issued' || status === 'partially_paid',
  };
}
