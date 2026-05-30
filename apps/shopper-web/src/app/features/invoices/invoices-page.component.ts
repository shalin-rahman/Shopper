import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule } from '@ngneat/transloco';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

@Component({
  selector: 'app-invoices-page',
  standalone: true,
  imports: [CommonModule, TranslocoModule, ShopperDataGridComponent, ShopperButtonComponent],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-3xl font-black tracking-tighter text-shopper-text uppercase">
            {{ 'nav.invoices' | transloco }}
          </h2>
          <p class="text-slate-400 font-medium">View sales history, print Mushak 6.3 Tax Invoices, and record payments.</p>
        </div>
        <div class="flex gap-3">
          <app-shopper-button variant="outline" (click)="loadInvoices()">
            {{ 'products.refresh' | transloco }}
          </app-shopper-button>
          <app-shopper-button variant="primary">
            Create Manual Invoice
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
          />
        }
      </div>
    </div>
  `
})
export class InvoicesPageComponent implements OnInit {
  private http = inject(HttpClient);
  
  invoices = signal<any[]>([]);
  loading = signal(false);

  columns = [
    { key: 'invoice_no', label: 'Invoice #', bold: true },
    { key: 'customer_name', label: 'Customer' },
    { key: 'total_amount', label: 'Total', type: 'currency', align: 'right' },
    { key: 'amount_paid', label: 'Paid', align: 'right' },
    { key: 'balance_due', label: 'Due', align: 'right' },
    { key: 'status', label: 'Status', pill: true },
    { key: 'created_at', label: 'Date', type: 'date' }
  ];

  ngOnInit() {
    this.loadInvoices();
  }

  loadInvoices() {
    this.loading.set(true);
    this.http.get<any[]>('/api/v1/tenant/invoices').subscribe({
      next: (data) => {
        this.invoices.set(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }
}
