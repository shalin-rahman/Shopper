import { Component, Input, ContentChild, TemplateRef } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-shopper-data-grid',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="overflow-x-auto rounded-xl border border-shopper-border bg-shopper-bg">
      <table class="min-w-full divide-y divide-shopper-border">
        <thead class="bg-shopper-surface">
          <tr>
            <th 
              *ngFor="let col of columns" 
              class="px-6 py-4 text-left text-xs font-bold text-shopper-text uppercase tracking-wider"
            >
              {{ col.header }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-shopper-border">
          <tr *ngFor="let item of data" class="hover:bg-shopper-surface transition-colors duration-150">
            <td *ngFor="let col of columns" class="px-6 py-4 whitespace-nowrap text-sm text-shopper-text">
              <ng-container *ngIf="col.template; else default">
                <ng-container *ngTemplateOutlet="col.template; context: { $implicit: item }"></ng-container>
              </ng-container>
              <ng-template #default>{{ item[col.field] }}</ng-template>
            </td>
          </tr>
        </tbody>
      </table>
      <div *ngIf="data.length === 0" class="p-12 text-center text-shopper-text/60 italic">
        No records found.
      </div>
    </div>
  `
})
export class ShopperDataGridComponent {
  @Input() data: any[] = [];
  @Input() columns: { field: string, header: string, template?: TemplateRef<any> }[] = [];
}
