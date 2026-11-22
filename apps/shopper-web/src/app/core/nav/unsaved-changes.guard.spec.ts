import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';

import { HasUnsavedChanges, unsavedChangesGuard } from './unsaved-changes.guard';

describe('unsavedChangesGuard', () => {
  const run = (dirty: boolean) =>
    TestBed.runInInjectionContext(() =>
      unsavedChangesGuard(
        { hasUnsavedChanges: () => dirty } as HasUnsavedChanges,
        {} as ActivatedRouteSnapshot,
        {} as RouterStateSnapshot,
        {} as RouterStateSnapshot,
      ),
    );

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        TranslocoTestingModule.forRoot({
          langs: { en: { settings: { leaveUnsaved: 'Leave?' } } },
          translocoConfig: { availableLangs: ['en'], defaultLang: 'en' },
          preloadLangs: true,
        }),
      ],
    });
  });

  it('lets the user leave without asking when nothing changed', () => {
    const confirm = spyOn(window, 'confirm');
    expect(run(false)).toBeTrue();
    expect(confirm).not.toHaveBeenCalled();
  });

  it('asks before leaving with changes and stays when the user says no', () => {
    const confirm = spyOn(window, 'confirm').and.returnValue(false);
    expect(run(true)).toBeFalse();
    expect(confirm).toHaveBeenCalledWith('Leave?');
  });

  it('leaves with changes when the user says yes', () => {
    spyOn(window, 'confirm').and.returnValue(true);
    expect(run(true)).toBeTrue();
  });
});
