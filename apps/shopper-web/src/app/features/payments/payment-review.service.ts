import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PaymentReview {
  id: string;
  gateway: string;
  amount: string;
  currency: string;
  status: string;
  invoice_id: string | null;
  review_reason: string;
  review_note: string | null;
  review_resolved_at: string | null;
  review_resolved_by: string | null;
  created_at: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class PaymentReviewService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  listOpen(): Observable<PaymentReview[]> {
    return this.http.get<PaymentReview[]>(`${this.base}/v1/tenant/payments/review`);
  }

  refund(id: string, amount: number, note: string): Observable<unknown> {
    return this.http.post(`${this.base}/v1/tenant/payments/${id}/refunds`, {
      amount: amount.toFixed(2),
      note: note.trim() || null,
    });
  }

  resolve(id: string, note: string): Observable<PaymentReview> {
    return this.http.post<PaymentReview>(`${this.base}/v1/tenant/payments/${id}/resolve-review`, {
      note: note.trim(),
    });
  }
}
