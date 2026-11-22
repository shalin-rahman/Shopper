/** @type {import('tailwindcss').Config} */

// Theme colors come from --shopper-* tokens in src/styles.scss. The tokens are hex,
// so opacity (bg-shopper-primary/10) is done with color-mix instead of rgb channels.
const token = (name) => ({ opacityValue }) =>
  opacityValue === undefined || opacityValue === '1'
    ? `var(--shopper-${name})`
    : `color-mix(in srgb, var(--shopper-${name}) calc(${opacityValue} * 100%), transparent)`;

module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        shopper: {
          primary: token('primary'),
          bg: token('bg'),
          text: token('text'),
          accent: token('accent'),
          surface: token('surface'),
          border: token('border'),
          muted: token('muted'),
        },
      },
    },
  },
  plugins: [],
}
