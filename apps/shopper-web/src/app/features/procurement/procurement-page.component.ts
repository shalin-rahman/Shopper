import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule } from '@ngneat/transloco';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

@Component({
  selector: 'app-procurement-page',
  standalone: true,
  imports: [CommonModule, TranslocoModule, ShopperDataGridComponent, ShopperButtonComponent],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 class="text-3xl font-black tracking-tighter text-shopper-text uppercase">
            {{ 'nav.procurement' | transloco }}
          </h2>
          <p class="text-shopper-muted font-medium">{{ 'procurement.subtitle' | transloco }}</p>
        </div>
        <div class="flex gap-3">
          <app-shopper-button variant="outline" (click)="loadAll()">
            {{ 'products.refresh' | transloco }}
          </app-shopper-button>
          <app-shopper-button variant="primary">
{{ 'procurement.newPo' | transloco }}
          </app-shopper-button>
        </div>
      </div>

      <!-- Procurement Tabs -->
      <div class="flex gap-1 p-1 bg-shopper-surface rounded-2xl w-fit max-w-full overflow-x-auto border border-shopper-border">
        <button 
          (click)="activeTab.set('pos')"
          class="px-4 sm:px-6 py-2 whitespace-nowrap rounded-xl text-xs font-black uppercase tracking-widest transition-all"
          [class.bg-shopper-primary]="activeTab() === 'pos'"
          [class.text-white]="activeTab() === 'pos'"
          [class.text-shopper-muted]="activeTab() !== 'pos'"
        >
{{ 'procurement.tabs.pos' | transloco }}
        </button>
        <button 
          (click)="activeTab.set('returns')"
          class="px-4 sm:px-6 py-2 whitespace-nowrap rounded-xl text-xs font-black uppercase tracking-widest transition-all"
          [class.bg-shopper-primary]="activeTab() === 'returns'"
          [class.text-white]="activeTab() === 'returns'"
          [class.text-shopper-muted]="activeTab() !== 'returns'"
        >
{{ 'procurement.tabs.returns' | transloco }}
        </button>
        <button 
          (click)="activeTab.set('payments')"
          class="px-4 sm:px-6 py-2 whitespace-nowrap rounded-xl text-xs font-black uppercase tracking-widest transition-all"
          [class.bg-shopper-primary]="activeTab() === 'payments'"
          [class.text-white]="activeTab() === 'payments'"
          [class.text-shopper-muted]="activeTab() !== 'payments'"
        >
{{ 'procurement.tabs.payments' | transloco }}
        </button>
      </div>

      <div class="bg-shopper-surface/50 rounded-[2rem] border border-shopper-border p-8 backdrop-blur-sm">
        @if (loading()) {
          <div class="py-20 flex justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-shopper-primary"></div>
          </div>
        } @else {
          @if (activeTab() === 'pos') {
            <app-shopper-data-grid 
              [data]="pos()"
              [columns]="poColumns"
            />
          } @else if (activeTab() === 'returns') {
            <app-shopper-data-grid 
              [data]="returns()"
              [columns]="returnColumns"
            />
          } @else if (activeTab() === 'payments') {
            <app-shopper-data-grid 
              [data]="payments()"
              [columns]="paymentColumns"
            />
          }
        }
      </div>
    </div>
  `
})
export class ProcurementPageComponent implements OnInit {
  private http = inject(HttpClient);
  
  activeTab = signal<'pos' | 'returns' | 'payments'>('pos');
  pos = signal<any[]>([]);
  returns = signal<any[]>([]);
  payments = signal<any[]>([]);
  loading = signal(false);

  poColumns = [
    { key: 'po_no', label: 'procurement.cols.poNo', bold: true },
    { key: 'supplier_name', label: 'procurement.cols.supplier' },
    { key: 'status', label: 'procurement.cols.status', pill: true },
    { key: 'total_amount', label: 'procurement.cols.amount', type: 'currency', align: 'right' },
    { key: 'balance_due', label: 'procurement.cols.due', align: 'right' },
    { key: 'created_at', label: 'procurement.cols.date', type: 'date' }
  ];

  returnColumns = [
    { key: 'note_no', label: 'procurement.cols.debitNoteNo', bold: true },
    { key: 'po_no', label: 'procurement.cols.poRef' },
    { key: 'reason', label: 'procurement.cols.reason' },
    { key: 'total_adjustment', label: 'procurement.cols.adjustment', align: 'right' },
    { key: 'created_at', label: 'procurement.cols.date', type: 'date' }
  ];

  paymentColumns = [
    { key: 'payment_no', label: 'procurement.cols.paymentNo', bold: true },
    { key: 'amount', label: 'procurement.cols.amount', type: 'currency', align: 'right' },
    { key: 'payment_method', label: 'procurement.cols.method' },
    { key: 'ref_no', label: 'procurement.cols.reference' },
    { key: 'created_at', label: 'procurement.cols.date', type: 'date' }
  ];

  ngOnInit() {
    this.loadAll();
  }

  loadAll() {
    this.loading.set(true);
    this.http.get<any[]>('/api/v1/tenant/procurement/po').subscribe({
      next: (data) => {
        this.pos.set(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });

    this.http.get<any[]>('/api/v1/tenant/procurement/returns').subscribe({
      next: (data) => this.returns.set(data),
      error: () => {}
    });

    this.http.get<any[]>('/api/v1/tenant/procurement/payments').subscribe({
      next: (data) => this.payments.set(data),
      error: () => {}
    });
  }
}
