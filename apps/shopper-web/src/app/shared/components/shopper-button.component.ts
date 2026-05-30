import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-shopper-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button
      [type]="type"
      [disabled]="disabled || loading"
      (click)="onClick($event)"
      class="relative w-full h-full px-6 py-3 rounded-xl font-bold transition-all duration-300 focus:outline-none focus:ring-4 disabled:opacity-70 disabled:cursor-not-allowed group overflow-hidden"
      [ngClass]="{
        'bg-shopper-primary text-white hover:bg-shopper-accent focus:ring-shopper-primary/20 shadow-lg shadow-shopper-primary/20': variant === 'primary',
        'bg-shopper-surface text-shopper-text hover:bg-shopper-border focus:ring-shopper-border/20': variant === 'secondary',
        'border-2 border-shopper-primary text-shopper-primary hover:bg-shopper-primary hover:text-white': variant === 'outline',
        'bg-transparent text-shopper-text hover:bg-shopper-surface': variant === 'ghost'
      }"
    >
      <div 
        class="absolute inset-0 bg-white/10 translate-y-full transition-transform duration-300 group-hover:translate-y-0"
      ></div>
      
      <div class="relative flex items-center justify-center gap-2 whitespace-nowrap">
        <span *ngIf="loading" class="animate-spin text-xl">◌</span>
        <ng-content></ng-content>
      </div>
    </button>
  `,
  styles: [
    `
      :host { display: inline-block; }
    `,
  ],
})
export class ShopperButtonComponent {
  @Input() variant: 'primary' | 'secondary' | 'outline' | 'ghost' = 'primary';
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() disabled = false;
  @Input() loading = false;
  @Output() btnClick = new EventEmitter<MouseEvent>();

  onClick(event: MouseEvent) {
    if (!this.disabled && !this.loading) {
      this.btnClick.emit(event);
    }
  }
}
