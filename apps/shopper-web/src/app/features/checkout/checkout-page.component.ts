import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { TranslocoPipe } from '@ngneat/transloco';

import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';
import { CheckoutGateway, CheckoutInvoice, CheckoutLinkParams, CheckoutService } from './checkout.service';

/** Leaves the app for the gateway's own payment page. Kept apart so tests can replace it. */
export const goToGateway = { open: (url: string) => window.location.assign(url) };

/** Only send the customer to a real https page, never a javascript: or http: link. */
function isHttps(url: string): boolean {
  try {
    return new URL(url).protocol === 'https:';
  } catch {
    return false;
  }
}

@Component({
  selector: 'app-checkout-page',
  standalone: true,
  imports: [CommonModule, TranslocoPipe, ShopperButtonComponent],
  template: `
    <div class="flex min-h-screen items-center justify-center bg-shopper-bg px-4 py-10">
      <div class="w-full max-w-md space-y-6 rounded-3xl border border-shopper-border bg-shopper-surface p-8 shadow-2xl">
        @if (state() === 'loading') {
          <div class="flex justify-center py-10">
            <div class="h-8 w-8 animate-spin rounded-full border-b-2 border-shopper-primary"></div>
          </div>
        } @else if (state() === 'badLink') {
          <p role="alert" class="text-center font-semibold text-red-500">{{ 'checkout.badLink' | transloco }}</p>
        } @else if (state() === 'error') {
          <p role="alert" class="text-center font-semibold text-red-500">{{ 'checkout.loadFailed' | transloco }}</p>
        } @else {
          @if (invoice(); as inv) {
          <div>
            <p class="text-xs font-bold uppercase tracking-widest text-slate-400">{{ 'checkout.invoice' | transloco }}</p>
            <h1 class="text-2xl font-extrabold tracking-tight text-shopper-text">{{ inv.invoice_no }}</h1>
          </div>
          <ul class="divide-y divide-shopper-border text-sm">
            @for (line of inv.lines; track line.id) {
              <li class="flex justify-between gap-4 py-2">
                <span>{{ line.description }} × {{ line.qty }}</span>
                <span class="font-semibold">৳ {{ line.line_total | number: '1.2-2' }}</span>
              </li>
            }
          </ul>
          <div class="flex justify-between border-t border-shopper-border pt-4 text-lg font-black">
            <span>{{ 'checkout.due' | transloco }}</span>
            <span class="text-shopper-primary">৳ {{ inv.balance_due | number: '1.2-2' }}</span>
          </div>
          @if (payable()) {
            <fieldset class="space-y-2">
              <legend class="mb-2 text-xs font-bold uppercase tracking-widest text-slate-400">{{ 'checkout.method' | transloco }}</legend>
              @for (g of gateways; track g.id) {
                <label
                  class="flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-bold transition-all"
                  [class.border-shopper-primary]="gateway() === g.id"
                  [class.border-shopper-border]="gateway() !== g.id"
                >
                  <input type="radio" name="gateway" [value]="g.id" [checked]="gateway() === g.id" (change)="gateway.set(g.id)" />
                  {{ g.label }}
                </label>
              }
            </fieldset>
            @if (payError(); as e) {
              <p role="alert" class="text-sm font-semibold text-red-500">{{ e.key ? (e.key | transloco) : e.text }}</p>
            }
            <app-shopper-button class="w-full" [disabled]="!gateway()" [loading]="paying()" (btnClick)="pay()">
              {{ 'checkout.pay' | transloco }}
            </app-shopper-button>
          } @else {
            <p class="text-center font-semibold text-slate-400">{{ 'checkout.nothingDue' | transloco }}</p>
          }
          }
        }
      </div>
    </div>
  `,
})
export class CheckoutPageComponent implements OnInit {
  private readonly api = inject(CheckoutService);
  private readonly route = inject(ActivatedRoute);

  readonly gateways: { id: CheckoutGateway; label: string }[] = [
    { id: 'bkash', label: 'bKash' },
    { id: 'nagad', label: 'Nagad' },
    { id: 'sslcommerz', label: 'Card / SSLCommerz' },
  ];

  readonly state = signal<'loading' | 'ready' | 'badLink' | 'error'>('loading');
  readonly invoice = signal<CheckoutInvoice | null>(null);
  readonly gateway = signal<CheckoutGateway | null>(null);
  readonly paying = signal(false);
  /** Our own messages are i18n keys. A reason sent by the server is shown as it came. */
  readonly payError = signal<{ key?: string; text?: string } | null>(null);

  private invoiceId = '';
  private link: CheckoutLinkParams = { t: '', e: '' };

  ngOnInit(): void {
    const snap = this.route.snapshot;
    this.invoiceId = snap.paramMap.get('id') ?? '';
    this.link = { t: snap.queryParamMap.get('t') ?? '', e: snap.queryParamMap.get('e') ?? '' };
    if (!this.link.t || !this.link.e) {
      this.state.set('badLink');
      return;
    }
    this.api.load(this.invoiceId, this.link).subscribe({
      next: (inv) => {
        this.invoice.set(inv);
        this.state.set('ready');
      },
      error: (err: unknown) => {
        const bad = err instanceof HttpErrorResponse && (err.status === 403 || err.status === 404);
        this.state.set(bad ? 'badLink' : 'error');
      },
    });
  }

  payable(): boolean {
    const inv = this.invoice();
    return !!inv && Number(inv.balance_due) > 0 && (inv.status === 'issued' || inv.status === 'partially_paid');
  }

  pay(): void {
    const inv = this.invoice();
    const gateway = this.gateway();
    if (!inv || !gateway || this.paying()) return;
    this.paying.set(true);
    this.payError.set(null);
    this.api.pay(this.invoiceId, this.link, gateway, inv.balance_due).subscribe({
      next: (res) => {
        if (res.gateway_url && isHttps(res.gateway_url)) {
          goToGateway.open(res.gateway_url);
          return;
        }
        this.paying.set(false);
        this.payError.set({ key: 'checkout.noPaymentPage' });
      },
      error: (err: unknown) => {
        this.paying.set(false);
        const detail = err instanceof HttpErrorResponse ? err.error?.detail : null;
        this.payError.set(typeof detail === 'string' ? { text: detail } : { key: 'checkout.payFailed' });
      },
    });
  }
}
