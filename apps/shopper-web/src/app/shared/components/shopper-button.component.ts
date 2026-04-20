import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-shopper-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button
      [type]="type"
      [disabled]="disabled"
      (click)="onClick($event)"
      class="px-4 py-2 rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed"
      [ngClass]="{
        'bg-shopper-primary text-white hover:bg-shopper-accent focus:ring-shopper-primary': variant === 'primary',
        'bg-shopper-surface text-shopper-text hover:bg-shopper-border focus:ring-shopper-border': variant === 'secondary',
        'border-2 border-shopper-primary text-shopper-primary hover:bg-shopper-primary hover:text-white': variant === 'outline'
      }"
    >
      <ng-content></ng-content>
    </button>
  `,
  styles: [
    `
      :host { display: inline-block; }
    `,
  ],
})
export class ShopperButtonComponent {
  @Input() variant: 'primary' | 'secondary' | 'outline' = 'primary';
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() disabled = false;
  @Output() clicked = new EventEmitter<MouseEvent>();

  onClick(event: MouseEvent) {
    if (!this.disabled) {
      this.clicked.emit(event);
    }
  }
}
