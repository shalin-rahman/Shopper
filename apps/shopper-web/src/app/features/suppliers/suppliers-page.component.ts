import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule } from '@ngneat/transloco';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

@Component({
  selector: 'app-suppliers-page',
  standalone: true,
  imports: [CommonModule, TranslocoModule, ShopperDataGridComponent, ShopperButtonComponent],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 class="text-3xl font-black tracking-tighter text-shopper-text uppercase">
            {{ 'nav.suppliers' | transloco }}
          </h2>
          <p class="text-shopper-muted font-medium">{{ 'suppliers.subtitle' | transloco }}</p>
        </div>
        <div class="flex flex-wrap gap-3">
          <app-shopper-button variant="outline" (click)="loadSuppliers()">
            {{ 'products.refresh' | transloco }}
          </app-shopper-button>
          <app-shopper-button variant="primary">
            {{ 'suppliers.addTitle' | transloco }}
          </app-shopper-button>
        </div>
      </div>

      <div class="bg-shopper-surface/50 rounded-[2rem] border border-shopper-border p-4 sm:p-8 backdrop-blur-sm">
        @if (loading()) {
          <div class="py-20 flex justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-shopper-primary"></div>
          </div>
        } @else {
          <app-shopper-data-grid 
            [data]="suppliers()"
            [columns]="columns"
          />
        }
      </div>
    </div>
  `
})
export class SuppliersPageComponent implements OnInit {
  private http = inject(HttpClient);
  
  suppliers = signal<any[]>([]);
  loading = signal(false);

  columns = [
    { key: 'code', label: 'suppliers.cols.code', bold: true },
    { key: 'name_en', label: 'suppliers.cols.nameEn' },
    { key: 'phone', label: 'suppliers.cols.phone' },
    { key: 'email', label: 'suppliers.cols.email' },
    { key: 'address', label: 'suppliers.cols.address' }
  ];

  ngOnInit() {
    this.loadSuppliers();
  }

  loadSuppliers() {
    this.loading.set(true);
    this.http.get<any>('/api/v1/tenant/suppliers').subscribe({
      next: (res) => {
        this.suppliers.set(res.items || []);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }
}
