import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule } from '@ngneat/transloco';
import { ShopperDataGridComponent } from '../../shared/components/shopper-data-grid.component';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

@Component({
  selector: 'app-staff-page',
  standalone: true,
  imports: [CommonModule, TranslocoModule, ShopperDataGridComponent, ShopperButtonComponent],
  template: `
    <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-3xl font-black tracking-tighter text-shopper-text uppercase">
            {{ 'nav.staff' | transloco }}
          </h2>
          <p class="text-slate-400 font-medium">Manage team members, roles, and system access.</p>
        </div>
        <div class="flex gap-3">
          <app-shopper-button variant="primary">
            {{ 'staff.addTitle' | transloco }}
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
            [data]="staff()"
            [columns]="columns"
          >
            <ng-template #actions let-row="row">
               <div class="flex gap-2 justify-end">
                   <app-shopper-button variant="outline" size="sm">Edit</app-shopper-button>
               </div>
            </ng-template>
          </app-shopper-data-grid>
        }
      </div>
    </div>
  `
})
export class StaffPageComponent implements OnInit {
  private http = inject(HttpClient);
  
  staff = signal<any[]>([]);
  loading = signal(false);

  columns = [
    { key: 'username', label: 'Username', bold: true },
    { key: 'full_name', label: 'Full Name' },
    { key: 'role', label: 'Role', pill: true },
    { key: 'is_active', label: 'Status', pill: true }
  ];

  ngOnInit() {
    this.loadStaff();
  }

  loadStaff() {
    this.loading.set(true);
    this.http.get<any>('/api/v1/tenant/staff').subscribe({
      next: (res) => {
        this.staff.set(res.items || []);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }
}
