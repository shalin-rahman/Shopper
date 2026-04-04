import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export type TenantLifecycleStatus = 'pending' | 'active' | 'suspended' | 'deleted';

export interface PlatformTenantRow {
  id: string;
  subdomain: string;
  display_name_en: string;
  display_name_bn: string;
  status: TenantLifecycleStatus;
  dedicated_database_name: string | null;
  created_at: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class AdminPlatformService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  listTenants(): Observable<PlatformTenantRow[]> {
    return this.http
      .get<{ items: PlatformTenantRow[] }>(`${this.base}/v1/admin/tenants`)
      .pipe(map((r) => r.items));
  }

  setTenantStatus(tenantId: string, status: TenantLifecycleStatus): Observable<PlatformTenantRow> {
    return this.http.patch<PlatformTenantRow>(`${this.base}/v1/admin/tenants/${tenantId}/status`, {
      status,
    });
  }
}
