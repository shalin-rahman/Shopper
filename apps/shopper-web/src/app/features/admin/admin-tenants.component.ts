import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslocoPipe } from '@ngneat/transloco';

import { SHOPPER_ADMIN_KEY_STORAGE } from '../../core/http/shopper-admin.interceptor';
import {
  AdminPlatformService,
  PlatformTenantRow,
  TenantLifecycleStatus,
} from './admin-platform.service';

@Component({
  selector: 'app-admin-tenants',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslocoPipe],
  templateUrl: './admin-tenants.component.html',
})
export class AdminTenantsComponent implements OnInit {
  private readonly adminApi = inject(AdminPlatformService);

  readonly items = signal<PlatformTenantRow[]>([]);
  readonly loadError = signal<string | null>(null);
  readonly keySaved = signal(false);
  readonly savingId = signal<string | null>(null);

  adminKeyInput = '';

  ngOnInit(): void {
    const existing = sessionStorage.getItem(SHOPPER_ADMIN_KEY_STORAGE);
    if (existing) {
      this.adminKeyInput = existing;
      this.keySaved.set(true);
      this.reload();
    }
  }

  saveKey(): void {
    const k = this.adminKeyInput.trim();
    if (!k) {
      sessionStorage.removeItem(SHOPPER_ADMIN_KEY_STORAGE);
      this.keySaved.set(false);
      this.items.set([]);
      return;
    }
    sessionStorage.setItem(SHOPPER_ADMIN_KEY_STORAGE, k);
    this.keySaved.set(true);
    this.reload();
  }

  clearKey(): void {
    sessionStorage.removeItem(SHOPPER_ADMIN_KEY_STORAGE);
    this.adminKeyInput = '';
    this.keySaved.set(false);
    this.items.set([]);
    this.loadError.set(null);
  }

  reload(): void {
    this.loadError.set(null);
    if (!sessionStorage.getItem(SHOPPER_ADMIN_KEY_STORAGE)?.trim()) {
      return;
    }
    this.adminApi.listTenants().subscribe({
      next: (rows) => this.items.set(rows),
      error: () => this.loadError.set('admin.loadFailed'),
    });
  }

  statuses(): TenantLifecycleStatus[] {
    return ['pending', 'active', 'suspended', 'deleted'];
  }

  statusLabelKey(s: TenantLifecycleStatus): string {
    const map: Record<TenantLifecycleStatus, string> = {
      pending: 'admin.statusPending',
      active: 'admin.statusActive',
      suspended: 'admin.statusSuspended',
      deleted: 'admin.statusDeleted',
    };
    return map[s];
  }

  onStatusSelectChange(row: PlatformTenantRow, ev: Event): void {
    const v = (ev.target as HTMLSelectElement).value as TenantLifecycleStatus;
    this.onStatusChange(row, v);
  }

  onStatusChange(row: PlatformTenantRow, status: TenantLifecycleStatus): void {
    if (row.status === status) {
      return;
    }
    this.savingId.set(row.id);
    this.adminApi.setTenantStatus(row.id, status).subscribe({
      next: (updated) => {
        this.items.update((list) => list.map((t) => (t.id === updated.id ? updated : t)));
        this.savingId.set(null);
      },
      error: () => {
        this.savingId.set(null);
        this.loadError.set('admin.saveFailed');
      },
    });
  }
}
