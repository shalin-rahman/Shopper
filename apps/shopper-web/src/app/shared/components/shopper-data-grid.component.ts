import { Component, Input, ContentChild, TemplateRef } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-shopper-data-grid',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative overflow-hidden rounded-3xl border border-shopper-border bg-shopper-bg/40 backdrop-blur-sm">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-shopper-border bg-shopper-surface/50">
              <th 
                *ngFor="let col of columns" 
                [style.width]="col.width || 'auto'"
                class="px-6 py-5 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400"
                [attr.align]="col.align || 'left'"
              >
                {{ col.label || col.header }}
              </th>
              <th *ngIf="actionsTemplate" class="px-6 py-5 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 text-right">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-shopper-border/50">
            <tr 
              *ngFor="let item of data" 
              class="group hover:bg-shopper-primary/5 transition-all duration-300"
            >
              <td 
                *ngFor="let col of columns" 
                class="px-6 py-4 text-sm text-shopper-text font-medium"
                [attr.align]="col.align || 'left'"
              >
                <ng-container *ngIf="cellTemplate; else default">
                  <ng-container *ngTemplateOutlet="cellTemplate; context: { row: item, col: col }"></ng-container>
                </ng-container>
                <ng-template #default>
                  <span [class.font-black]="col.bold" [class.text-shopper-primary]="col.bold">
                    @if (col.pill) {
                        <span class="inline-flex items-center rounded-full bg-shopper-primary/10 px-2.5 py-0.5 text-xs font-bold text-shopper-primary uppercase tracking-tighter">
                            {{ item[col.key] }}
                        </span>
                    } @else if (col.type === 'currency') {
                        ৳ {{ item[col.key] | number:'1.2-2' }}
                    } @else if (col.type === 'date') {
                        {{ item[col.key] | date:'mediumDate' }}
                    } @else {
                        {{ item[col.key] }}
                    }
                  </span>
                </ng-template>
              </td>
              <td *ngIf="actionsTemplate" class="px-6 py-4 text-right">
                <ng-container *ngTemplateOutlet="actionsTemplate; context: { row: item }"></ng-container>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div *ngIf="data.length === 0" class="flex flex-col items-center justify-center p-20 text-slate-300">
        <span class="text-4xl mb-2">🔭</span>
        <p class="text-sm font-medium italic">No matches found in this universe.</p>
      </div>
    </div>
  `,
  styles: [`
    td { transition: transform 0.2s; }
    tr:hover td { transform: translateX(2px); }
  `]
})
export class ShopperDataGridComponent {
  @Input() data: any[] = [];
  @Input() columns: any[] = [];
  
  @ContentChild('cell') cellTemplate?: TemplateRef<any>;
  @ContentChild('actions') actionsTemplate?: TemplateRef<any>;
}
