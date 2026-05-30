import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule } from '@ngneat/transloco';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

@Component({
  selector: 'app-accounting-page',
  standalone: true,
  imports: [CommonModule, TranslocoModule, ShopperDataGridComponent, ShopperButtonComponent],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-3xl font-black tracking-tighter text-shopper-text uppercase">
            {{ 'nav.accounting' | transloco }}
          </h2>
          <p class="text-slate-400 font-medium">Manage your system accounts and double-entry ledger.</p>
        </div>
        <div class="flex gap-3">
          <app-shopper-button variant="outline" (click)="loadAccounts()">
            {{ 'products.refresh' | transloco }}
          </app-shopper-button>
          <app-shopper-button variant="primary">
            New Journal Entry
          </app-shopper-button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Dashboard Summary Cards -->
        <div class="p-6 rounded-3xl bg-shopper-surface border border-shopper-border shadow-sm">
          <p class="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">Total Assets</p>
          <h3 class="text-2xl font-black text-shopper-primary">৳ {{ totalAssets() | number:'1.2-2' }}</h3>
        </div>
        <div class="p-6 rounded-3xl bg-shopper-surface border border-shopper-border shadow-sm">
          <p class="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">Total Liabilities</p>
          <h3 class="text-2xl font-black text-red-500">৳ {{ totalLiabilities() | number:'1.2-2' }}</h3>
        </div>
        <div class="p-6 rounded-3xl bg-shopper-surface border border-shopper-border shadow-sm">
          <p class="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">Net Equity</p>
          <h3 class="text-2xl font-black text-emerald-500">৳ {{ (totalAssets() - totalLiabilities()) | number:'1.2-2' }}</h3>
        </div>
      </div>

      <div class="bg-shopper-surface/50 rounded-[2rem] border border-shopper-border p-8 backdrop-blur-sm">
        <h3 class="text-lg font-bold mb-6 flex items-center gap-2">
          <span class="h-2 w-2 rounded-full bg-shopper-primary"></span>
          Chart of Accounts
        </h3>
        
        @if (loading()) {
          <div class="py-20 flex justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-shopper-primary"></div>
          </div>
        } @else {
          <app-shopper-data-grid 
            [data]="accounts()"
            [columns]="columns"
          />
        }
      </div>
    </div>
  `
})
export class AccountingPageComponent implements OnInit {
  private http = inject(HttpClient);
  
  accounts = signal<any[]>([]);
  loading = signal(false);
  
  totalAssets = signal(0);
  totalLiabilities = signal(0);

  columns = [
    { key: 'code', label: 'Code', bold: true },
    { key: 'name_en', label: 'Name (EN)' },
    { key: 'name_bn', label: 'Name (BN)' },
    { key: 'account_type', label: 'Type', pill: true },
    { key: 'current_balance', label: 'Balance (BDT)', type: 'currency', align: 'right' }
  ];

  ngOnInit() {
    this.loadAccounts();
  }

  loadAccounts() {
    this.loading.set(true);
    // In a real app, the tenant_id is handled by the URL or a header
    this.http.get<any>('/api/v1/tenant/accounts').subscribe({
      next: (res) => {
        const items = res.items || [];
        this.accounts.set(items);
        
        let assets = 0;
        let liabilities = 0;
        items.forEach((a: any) => {
          const bal = parseFloat(a.current_balance);
          if (a.account_type === 'asset') assets += bal;
          if (a.account_type === 'liability') liabilities += bal;
        });
        this.totalAssets.set(assets);
        this.totalLiabilities.set(liabilities);
        
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }
}
