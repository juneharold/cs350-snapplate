/**
 * Real brand marks for OAuth buttons.
 *
 * Lucide ships a fruit-shaped `Apple` and a Chrome browser icon, neither
 * of which is what users expect on a sign-in screen. These inline SVGs
 * are the official Apple silhouette and Google's 4-color "G", scaled
 * to match lucide's 24-grid so they slot in next to the other icons.
 */

export function AppleLogo({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M16 3c-1 1.4-2.5 2-4 2 0-1.5 1-3 2.5-4 1.5 0 1.5 2 1.5 2z" />
      <path d="M19 16c-1 3-3 5-5 5-1.5 0-2-1-3.5-1S8.5 21 7 21c-2 0-4-3-4-7s2-7 5-7c1.5 0 2.5 1 3.5 1s1.5-1 3-1c2 0 3.5 1 4.5 3-3 1.5-3 5 0 6z" />
    </svg>
  );
}

export function GoogleLogo({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        d="M21.8 12.23c0-.71-.06-1.4-.18-2.05H12v3.88h5.5c-.24 1.27-.96 2.34-2.04 3.06v2.55h3.3c1.93-1.78 3.04-4.4 3.04-7.44z"
        fill="#4285F4"
      />
      <path
        d="M12 22c2.76 0 5.07-.92 6.76-2.49l-3.3-2.55c-.91.61-2.08.97-3.46.97-2.66 0-4.92-1.8-5.72-4.22H2.85v2.65A9.99 9.99 0 0 0 12 22z"
        fill="#34A853"
      />
      <path
        d="M6.28 13.71a6.01 6.01 0 0 1 0-3.82V7.24H2.85a10 10 0 0 0 0 9.52l3.43-3.05z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.97c1.5 0 2.85.52 3.91 1.53l2.93-2.93C17.06 2.97 14.76 2 12 2 8.13 2 4.77 4.22 2.85 7.24l3.43 2.65C7.08 7.77 9.34 5.97 12 5.97z"
        fill="#EA4335"
      />
    </svg>
  );
}
