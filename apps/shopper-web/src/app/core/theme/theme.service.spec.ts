import { TestBed } from '@angular/core/testing';
import { ThemeService, ShopperTheme, isShopperTheme } from './theme.service';

describe('ThemeService', () => {
  let service: ThemeService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    localStorage.clear();
    service = TestBed.inject(ThemeService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should have default theme initially', () => {
    expect(service.currentTheme()).toBe('default');
  });

  it('should change theme and update localStorage', () => {
    const targetTheme: ShopperTheme = 'cyberpunk';
    service.setTheme(targetTheme);
    
    expect(service.currentTheme()).toBe(targetTheme);
    expect(localStorage.getItem('shopper_web_theme')).toBe(targetTheme);
    expect(document.documentElement.getAttribute('data-theme')).toBe(targetTheme);
  });

  it('should toggle midnight theme', () => {
    service.setTheme('default');
    service.toggleDarkMode();
    expect(service.currentTheme()).toBe('midnight');
    
    service.toggleDarkMode();
    expect(service.currentTheme()).toBe('default');
  });

  it('has no saved theme until the user picks one', () => {
    expect(service.hasSavedTheme()).toBeFalse();
    service.setTheme('ruby');
    expect(service.hasSavedTheme()).toBeTrue();
  });

  it('applies a theme without saving it when persist is false', () => {
    service.setTheme('ocean', { persist: false });
    expect(service.currentTheme()).toBe('ocean');
    expect(document.documentElement.getAttribute('data-theme')).toBe('ocean');
    expect(localStorage.getItem('shopper_web_theme')).toBeNull();
    expect(service.hasSavedTheme()).toBeFalse();
  });

  it('ignores an unknown saved value', () => {
    localStorage.setItem('shopper_web_theme', 'neon');
    const fresh = new ThemeService();
    expect(fresh.currentTheme()).toBe('default');
    expect(fresh.hasSavedTheme()).toBeFalse();
  });

  it('restores a valid saved theme', () => {
    localStorage.setItem('shopper_web_theme', 'forest');
    expect(new ThemeService().currentTheme()).toBe('forest');
  });

  it('starts with the default theme when storage throws', () => {
    spyOn(localStorage, 'getItem').and.throwError('blocked');
    const fresh = new ThemeService();
    expect(fresh.currentTheme()).toBe('default');
    expect(fresh.hasSavedTheme()).toBeFalse();
  });

  it('checks theme ids', () => {
    expect(isShopperTheme('gold')).toBeTrue();
    expect(isShopperTheme('neon')).toBeFalse();
    expect(isShopperTheme(null)).toBeFalse();
  });
});
