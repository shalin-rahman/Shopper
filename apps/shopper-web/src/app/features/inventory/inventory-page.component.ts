import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule } from '@ngneat/transloco';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

@Component({
  selector: 'app-inventory-page',
  standalone: true,
  imports: [CommonModule, TranslocoModule, ShopperDataGridComponent, ShopperButtonComponent],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-3xl font-black tracking-tighter text-shopper-text uppercase">
            {{ 'nav.inventory' | transloco }}
          </h2>
          <p class="text-slate-400 font-medium">Manage non-monetary stock movements: Damaged, Lost, and Gifts.</p>
        </div>
        <div class="flex gap-3">
          <app-shopper-button variant="outline" (click)="loadHistory()">
            {{ 'products.refresh' | transloco }}
          </app-shopper-button>
          <app-shopper-button variant="primary">
            Record Adjustment
          </app-shopper-button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="p-6 rounded-3xl bg-shopper-surface border border-shopper-border shadow-sm">
          <p class="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">Damaged/Lost</p>
          <h3 class="text-2xl font-black text-red-500">{{ stats().damaged }} pcs</h3>
        </div>
        <div class="p-6 rounded-3xl bg-shopper-surface border border-shopper-border shadow-sm">
          <p class="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">Gifts Given</p>
          <h3 class="text-2xl font-black text-shopper-primary">{{ stats().gifts_out }} pcs</h3>
        </div>
        <div class="p-6 rounded-3xl bg-shopper-surface border border-shopper-border shadow-sm">
          <p class="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">Stock Expired</p>
          <h3 class="text-2xl font-black text-amber-500">{{ stats().expired }} pcs</h3>
        </div>
        <div class="p-6 rounded-3xl bg-shopper-surface border border-shopper-border shadow-sm">
          <p class="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">Bonus Received</p>
          <h3 class="text-2xl font-black text-emerald-500">{{ stats().gifts_in }} pcs</h3>
        </div>
      </div>

      <div class="bg-shopper-surface/50 rounded-[2rem] border border-shopper-border p-8 backdrop-blur-sm">
        <h3 class="text-lg font-bold mb-6 flex items-center gap-2">
          <span class="h-2 w-2 rounded-full bg-shopper-primary"></span>
          Stock Transaction Audit Log
        </h3>
        
        @if (loading()) {
          <div class="py-20 flex justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-shopper-primary"></div>
          </div>
        } @else {
          <app-shopper-data-grid 
            [data]="history()"
            [columns]="columns"
          />
        }
      </div>
    </div>
  `
})
export class InventoryPageComponent implements OnInit {
  private http = inject(HttpClient);
  
  history = signal<any[]>([]);
  loading = signal(false);
  stats = signal({ damaged: 0, gifts_out: 0, expired: 0, gifts_in: 0 });

  columns = [
    { key: 'sku', label: 'SKU', bold: true },
    { key: 'name_en', label: 'Product' },
    { key: 'transaction_type', label: 'Type', pill: true },
    { key: 'quantity', label: 'Qty', align: 'right' },
    { key: 'reason_code', label: 'Reason' },
    { key: 'created_at', label: 'Date', type: 'date' }
  ];

  ngOnInit() {
    this.loadHistory();
  }

  loadHistory() {
    this.loading.set(true);
    // Fetch from inventory router
    this.http.get<any[]>('/api/v1/tenant/inventory/history').subscribe({
      next: (data) => {
        this.history.set(data);
        this.calculateStats(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  private calculateStats(data: any[]) {
    const s = { damaged: 0, gifts_out: 0, expired: 0, gifts_in: 0 };
    data.forEach(tx => {
      const q = Math.abs(parseFloat(tx.quantity));
      if (tx.transaction_type === 'damage') s.damaged += q;
      if (tx.transaction_type === 'gift_out') s.gifts_out += q;
      if (tx.transaction_type === 'expired') s.expired += q;
      if (tx.transaction_type === 'gift_in') s.gifts_in += q;
    });
    this.stats.set(s);
  }
}
