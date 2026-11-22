import { Component, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslocoPipe } from '@ngneat/transloco';

import { AuthService } from '../../core/auth/auth.service';
import { TenantSettingsStore } from '../../core/tenant/tenant-settings.store';
import { ShopperButtonComponent } from '../../shared/components/shopper-button.component';

/** Only same-app paths are allowed as the page to return to. */
function safeNext(next: string | null): string {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/';
}

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [FormsModule, TranslocoPipe, ShopperButtonComponent],
  template: `
    <div class="flex min-h-screen items-center justify-center bg-shopper-bg px-6">
      <form
        class="w-full max-w-sm space-y-6 rounded-3xl border border-shopper-border bg-shopper-surface p-8 shadow-2xl"
        (ngSubmit)="submit()"
      >
        <h1 class="text-2xl font-extrabold tracking-tight text-shopper-text">{{ 'login.title' | transloco }}</h1>
        <div class="space-y-2">
          <label for="login-username" class="text-xs font-bold uppercase tracking-widest text-slate-400">
            {{ 'login.username' | transloco }}
          </label>
          <input
            id="login-username"
            name="username"
            autocomplete="username"
            required
            [(ngModel)]="username"
            class="w-full rounded-2xl border border-shopper-border bg-shopper-bg px-5 py-3 text-sm text-shopper-text outline-none focus:border-shopper-primary focus:ring-4 focus:ring-shopper-primary/10"
          />
        </div>
        <div class="space-y-2">
          <label for="login-password" class="text-xs font-bold uppercase tracking-widest text-slate-400">
            {{ 'login.password' | transloco }}
          </label>
          <input
            id="login-password"
            name="password"
            type="password"
            autocomplete="current-password"
            required
            [(ngModel)]="password"
            class="w-full rounded-2xl border border-shopper-border bg-shopper-bg px-5 py-3 text-sm text-shopper-text outline-none focus:border-shopper-primary focus:ring-4 focus:ring-shopper-primary/10"
          />
        </div>
        @if (error()) {
          <p role="alert" class="text-sm font-semibold text-red-500">{{ error()! | transloco }}</p>
        }
        <app-shopper-button class="w-full" type="submit" [loading]="busy()" [disabled]="!username.trim() || !password">
          {{ 'login.submit' | transloco }}
        </app-shopper-button>
      </form>
    </div>
  `,
})
export class LoginPageComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly store = inject(TenantSettingsStore);

  username = '';
  password = '';
  readonly busy = signal(false);
  readonly error = signal<string | null>(null);

  submit(): void {
    if (this.busy() || !this.username.trim() || !this.password) return;
    this.busy.set(true);
    this.error.set(null);
    this.auth.login(this.username, this.password).subscribe({
      next: () => {
        // Apply the shop's theme and language before the first page shows.
        void this.store.load().then(() => {
          this.busy.set(false);
          void this.router.navigateByUrl(safeNext(this.route.snapshot.queryParamMap.get('next')));
        });
      },
      error: (err: unknown) => {
        this.busy.set(false);
        this.password = '';
        const bad = err instanceof HttpErrorResponse && (err.status === 401 || err.status === 403);
        this.error.set(bad ? 'login.badCredentials' : 'login.failed');
      },
    });
  }
}
