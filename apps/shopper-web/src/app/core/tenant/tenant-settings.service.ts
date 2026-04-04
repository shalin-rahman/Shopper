import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface TenantSettingsDto {
  tenant_id: string;
  theme_id: string;
  default_language: string;
  logo_url: string | null;
  legal_title_en: string | null;
  legal_title_bn: string | null;
  bin: string | null;
  default_vat_rate_pct: string;
  module_access: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class TenantSettingsService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  load(): Observable<TenantSettingsDto> {
    return this.http.get<TenantSettingsDto>(`${this.base}/v1/tenant/settings`);
  }
}
