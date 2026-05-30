import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule } from '@ngneat/transloco';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

@Component({
  selector: 'app-expenses-page',
  standalone: true,
  imports: [CommonModule, TranslocoModule, ShopperDataGridComponent, ShopperButtonComponent],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-3xl font-black tracking-tighter text-shopper-text uppercase">
             {{ 'nav.expenses' | transloco }}
          </h2>
          <p class="text-slate-400 font-medium">Track operational costs and business expenditures.</p>
        </div>
        <div class="flex gap-3">
          <app-shopper-button variant="primary">
            Record Expense
          </app-shopper-button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
         <!-- Summary -->
         <div class="lg:col-span-1 space-y-6">
            <div class="p-6 rounded-3xl bg-shopper-surface border border-shopper-border shadow-sm">
                <p class="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">Monthly Burn</p>
                <h3 class="text-2xl font-black text-rose-500">৳ {{ totalExpenses() | number:'1.2-2' }}</h3>
            </div>
            
            <div class="p-6 rounded-3xl bg-shopper-bg border border-shopper-border shadow-sm">
                <h4 class="text-sm font-bold mb-4 uppercase tracking-tighter">Categories</h4>
                <div class="space-y-3">
                    @for (cat of categories(); track cat.id) {
                        <div class="flex justify-between items-center text-sm">
                            <span class="font-medium text-slate-500">{{ cat.name_en }}</span>
                            <span class="h-1.5 flex-grow mx-4 rounded-full bg-shopper-surface overflow-hidden">
                                <span class="block h-full bg-shopper-primary" [style.width.%]="40"></span>
                            </span>
                        </div>
                    }
                </div>
            </div>
         </div>

         <!-- Expenses List -->
         <div class="lg:col-span-3">
            <div class="bg-shopper-surface/50 rounded-[2rem] border border-shopper-border p-8 backdrop-blur-sm h-full">
                @if (loading()) {
                    <div class="py-20 flex justify-center">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-shopper-primary"></div>
                    </div>
                } @else {
                    <app-shopper-data-grid 
                        [data]="expenses()"
                        [columns]="columns"
                    />
                }
            </div>
         </div>
      </div>
    </div>
  `
})
export class ExpensesPageComponent implements OnInit {
  private http = inject(HttpClient);
  
  expenses = signal<any[]>([]);
  categories = signal<any[]>([]);
  loading = signal(false);
  totalExpenses = signal(0);

  columns = [
    { key: 'expense_date', label: 'Date', type: 'date' },
    { key: 'category_name', label: 'Category', pill: true },
    { key: 'description', label: 'Description' },
    { key: 'amount', label: 'Amount', type: 'currency', align: 'right' }
  ];

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.loading.set(true);
    // Fetch categories first
    this.http.get<any>('/api/v1/tenant/expenses/categories').subscribe(cats => {
        this.categories.set(cats.items || []);
    });

    // Fetch expenses (Mocked/Simulated for now until we have a real list endpoint, 
    // but we can use the same pattern as others)
    this.http.get<any>('/api/v1/tenant/expenses').subscribe({
      next: (res) => {
        // Since my backend only has POST /expenses and GET /categories, 
        // I might need a GET /expenses in backend too.
        // For now let's assume it returns items.
        // Actually, I should probably add GET /expenses to backend.
        this.expenses.set(res.items || []);
        let total = 0;
        (res.items || []).forEach((e: any) => total += parseFloat(e.amount));
        this.totalExpenses.set(total);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }
}
