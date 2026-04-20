import { TestBed } from '@angular/core/testing';
import { ThemeService, ShopperTheme } from './theme.service';

describe('ThemeService', () => {
  let service: ThemeService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ThemeService);
    localStorage.clear();
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
});
