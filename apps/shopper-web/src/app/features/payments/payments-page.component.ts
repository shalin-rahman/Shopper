import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslocoPipe } from '@ngneat/transloco';

import { LocaleService } from '../../core/i18n/locale.service';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { PaymentReview, PaymentReviewService } from './payment-review.service';

@Component({
  selector: 'app-payments-page',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslocoPipe, ShopperButtonComponent, ShopperDataGridComponent],
  templateUrl: './payments-page.component.html',
})
export class PaymentsPageComponent implements OnInit {
  private readonly reviewsApi = inject(PaymentReviewService);
  readonly locale = inject(LocaleService);

  readonly reviews = signal<PaymentReview[]>([]);
  readonly loaded = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly rowError = signal<{ id: string; key: string } | null>(null);
  readonly resolving = signal<string | null>(null);
  /** Result of the last refund. `text` is the API's own reason and wins over `key`. */
  readonly refundMsg = signal<{ id: string; key: string; text?: string; error: boolean } | null>(null);

  notes: Record<string, string> = {};
  refundAmounts: Record<string, number | null> = {};

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loadError.set(null);
    this.reviewsApi.listOpen().subscribe({
      next: (rows) => {
        this.reviews.set(rows);
        this.loaded.set(true);
      },
      error: () => this.loadError.set('payments.loadFailed'),
    });
  }

  received(r: PaymentReview): string {
    return this.locale.formatDate(new Date(r.created_at), 'short');
  }

  refund(r: PaymentReview): void {
    this.refundMsg.set(null);
    const amount = Number(this.refundAmounts[r.id]);
    if (!(amount > 0)) {
      this.refundMsg.set({ id: r.id, key: 'payments.refundAmountRequired', error: true });
      return;
    }
    this.resolving.set(r.id);
    this.reviewsApi.refund(r.id, amount, this.notes[r.id] ?? '').subscribe({
      next: () => {
        this.refundMsg.set({ id: r.id, key: 'payments.refunded', error: false });
        this.refundAmounts[r.id] = null;
        this.resolving.set(null);
      },
      error: (err: unknown) => {
        const detail = err instanceof HttpErrorResponse ? err.error?.detail : undefined;
        this.refundMsg.set({
          id: r.id,
          key: 'payments.refundFailed',
          text: typeof detail === 'string' ? detail : undefined,
          error: true,
        });
        this.resolving.set(null);
      },
    });
  }

  resolve(r: PaymentReview): void {
    this.rowError.set(null);
    const note = (this.notes[r.id] ?? '').trim();
    if (!note) {
      this.rowError.set({ id: r.id, key: 'payments.noteRequired' });
      return;
    }
    this.resolving.set(r.id);
    this.reviewsApi.resolve(r.id, note).subscribe({
      next: () => {
        this.reviews.update((rows) => rows.filter((x) => x.id !== r.id));
        delete this.notes[r.id];
        this.resolving.set(null);
      },
      error: () => {
        this.rowError.set({ id: r.id, key: 'payments.resolveFailed' });
        this.resolving.set(null);
      },
    });
  }
}
