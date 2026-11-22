import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';
import { InvoiceRow, InvoiceService, invoiceActions } from './invoice.service';

@Component({
  selector: 'app-invoices-page',
  standalone: true,
  imports: [CommonModule, TranslocoModule, ShopperDataGridComponent, ShopperButtonComponent],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 class="text-3xl font-black tracking-tighter text-shopper-text uppercase">
            {{ 'nav.invoices' | transloco }}
          </h2>
          <p class="text-shopper-muted font-medium">{{ 'invoices.subtitle' | transloco }}</p>
        </div>
        <div class="flex gap-3">
          <app-shopper-button variant="outline" (click)="loadInvoices()">
            {{ 'products.refresh' | transloco }}
          </app-shopper-button>
          <app-shopper-button variant="primary">
{{ 'invoices.createManual' | transloco }}
          </app-shopper-button>
        </div>
      </div>

      <div class="bg-shopper-surface/50 rounded-[2rem] border border-shopper-border p-8 backdrop-blur-sm">
        @if (loading()) {
          <div class="py-20 flex justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-shopper-primary"></div>
          </div>
        } @else {
          <app-shopper-data-grid
            [data]="invoices()"
            [columns]="columns"
          >
            <ng-template #actions let-row="row">
              <div class="flex flex-wrap justify-end gap-2">
                @if (can(row).issue) {
                  <app-shopper-button variant="outline" [loading]="busyId() === row.id" [disabled]="!!busyId()" (btnClick)="issue(row)">
                    {{ 'invoices.issue' | transloco }}
                  </app-shopper-button>
                }
                @if (can(row).cancel) {
                  <app-shopper-button variant="ghost" [disabled]="!!busyId()" (btnClick)="cancel(row)">
                    {{ 'invoices.cancel' | transloco }}
                  </app-shopper-button>
                }
                @if (can(row).payLink) {
                  <app-shopper-button variant="secondary" [disabled]="!!busyId()" (btnClick)="payLink(row)">
                    {{ 'invoices.payLink' | transloco }}
                  </app-shopper-button>
                }
              </div>
              @if (rowMessage()[row.id]; as msg) {
                <p class="mt-2 max-w-xs break-all text-right text-xs font-semibold" [class.text-red-500]="msg.error" [class.text-shopper-primary]="!msg.error">
                  {{ msg.text }}
                </p>
              }
            </ng-template>
          </app-shopper-data-grid>
        }
      </div>
    </div>
  `
})
export class InvoicesPageComponent implements OnInit {
  private readonly api = inject(InvoiceService);
  private readonly i18n = inject(TranslocoService);

  invoices = signal<InvoiceRow[]>([]);
  loading = signal(false);
  readonly busyId = signal<string | null>(null);
  readonly rowMessage = signal<Record<string, { text: string; error: boolean }>>({});

  columns = [
    { key: 'invoice_no', label: 'invoices.cols.invoiceNo', bold: true },
    { key: 'customer_name', label: 'invoices.cols.customer' },
    { key: 'total_amount', label: 'invoices.cols.total', type: 'currency', align: 'right' },
    { key: 'amount_paid', label: 'invoices.cols.paid', align: 'right' },
    { key: 'balance_due', label: 'invoices.cols.due', align: 'right' },
    { key: 'status', label: 'invoices.cols.status', pill: true },
    { key: 'created_at', label: 'invoices.cols.date', type: 'date' }
  ];

  ngOnInit() {
    this.loadInvoices();
  }

  can(row: InvoiceRow) {
    return invoiceActions(row.status);
  }

  loadInvoices() {
    this.loading.set(true);
    this.api.list().subscribe({
      next: (data) => {
        this.invoices.set(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  issue(row: InvoiceRow) {
    this.runOnRow(row, this.api.issue(row.id));
  }

  cancel(row: InvoiceRow) {
    if (!window.confirm(this.i18n.translate('invoices.confirmCancel', { no: row.invoice_no }))) return;
    this.runOnRow(row, this.api.cancel(row.id));
  }

  payLink(row: InvoiceRow) {
    this.busyId.set(row.id);
    this.api.checkoutLink(row.id).subscribe({
      next: (link) => {
        this.busyId.set(null);
        const url = `${window.location.origin}${link.path}`;
        // Show the link too, in case the browser blocks clipboard access.
        navigator.clipboard?.writeText(url).catch(() => undefined);
        this.setMessage(row.id, url, false);
      },
      error: (err: unknown) => {
        this.busyId.set(null);
        this.setMessage(row.id, apiError(err) ?? this.i18n.translate('invoices.requestFailed'), true);
      },
    });
  }

  private runOnRow(row: InvoiceRow, call: Observable<InvoiceRow>) {
    this.busyId.set(row.id);
    this.setMessage(row.id, null, false);
    call.subscribe({
      next: (updated) => {
        this.busyId.set(null);
        this.invoices.update((rows) => rows.map((r) => (r.id === updated.id ? { ...r, ...updated } : r)));
      },
      error: (err: unknown) => {
        this.busyId.set(null);
        this.setMessage(row.id, apiError(err) ?? this.i18n.translate('invoices.requestFailed'), true);
      },
    });
  }

  private setMessage(id: string, text: string | null, error: boolean) {
    this.rowMessage.update((all) => {
      const next = { ...all };
      if (text === null) delete next[id];
      else next[id] = { text, error };
      return next;
    });
  }
}

/** The API's own reason, e.g. "Not enough stock for SKU ...", or null when it sent none. */
function apiError(err: unknown): string | null {
  if (err instanceof HttpErrorResponse && typeof err.error?.detail === 'string') return err.error.detail;
  return null;
}
