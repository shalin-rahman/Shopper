import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule } from '@ngneat/transloco';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

@Component({
  selector: 'app-customers-page',
  standalone: true,
  imports: [CommonModule, TranslocoModule, ShopperDataGridComponent, ShopperButtonComponent],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-3xl font-black tracking-tighter text-shopper-text uppercase">
            {{ 'nav.customers' | transloco }}
          </h2>
          <p class="text-slate-400 font-medium">Manage customer relationships and credit collections.</p>
        </div>
        <div class="flex gap-3">
          <app-shopper-button variant="primary">
             {{ 'customers.addTitle' | transloco }}
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
            [data]="customers()"
            [columns]="columns"
          />
        }
      </div>
    </div>
  `
})
export class CustomersPageComponent implements OnInit {
  private http = inject(HttpClient);
  
  customers = signal<any[]>([]);
  loading = signal(false);

  columns = [
    { key: 'code', label: 'Code', bold: true },
    { key: 'name_en', label: 'Name (EN)' },
    { key: 'phone', label: 'Phone' },
    { key: 'email', label: 'Email' },
    { key: 'billing_address_en', label: 'Address' }
  ];

  ngOnInit() {
    this.loadCustomers();
  }

  loadCustomers() {
    this.loading.set(true);
    this.http.get<any[]>('/api/v1/tenant/customers').subscribe({
      next: (res) => {
        this.customers.set(res || []);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }
}
