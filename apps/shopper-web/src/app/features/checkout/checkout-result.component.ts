import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { TranslocoPipe } from '@ngneat/transloco';

type ResultStatus = 'success' | 'fail' | 'cancel' | 'unknown';

const KNOWN: ResultStatus[] = ['success', 'fail', 'cancel'];

/** Where the customer lands after the gateway. The API return route redirects here. */
@Component({
  selector: 'app-checkout-result',
  standalone: true,
  imports: [TranslocoPipe],
  template: `
    <div class="flex min-h-screen items-center justify-center bg-shopper-bg px-4 py-10">
      <div class="w-full max-w-md space-y-4 rounded-3xl border border-shopper-border bg-shopper-surface p-8 text-center shadow-2xl">
        <p
          role="status"
          class="text-lg font-extrabold"
          [class.text-shopper-primary]="status() === 'success'"
          [class.text-red-500]="status() !== 'success'"
        >
          {{ 'checkout.result.' + status() | transloco }}
        </p>
        @if (status() !== 'unknown') {
          <p class="text-sm text-shopper-muted">{{ 'checkout.result.pending' | transloco }}</p>
        }
      </div>
    </div>
  `,
})
export class CheckoutResultComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);

  readonly status = signal<ResultStatus>('unknown');

  ngOnInit(): void {
    const raw = this.route.snapshot.queryParamMap.get('status') as ResultStatus | null;
    this.status.set(raw && KNOWN.includes(raw) ? raw : 'unknown');
  }
}
