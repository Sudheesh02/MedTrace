import { Public_Sans } from 'next/font/google';
import './globals.css';

const publicSans = Public_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-sans',
});

export const metadata = {
  title: 'MedTrace | Stock-integrity triage for essential medicines',
  description: 'Alerts, Investigator vs Skeptic verdicts, decision traces and memory evidence from MedTrace runs. Inventory data is simulated.',
  applicationName: 'MedTrace',
  icons: { icon: '/icon.svg', apple: '/icon.svg' },
};

export const viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F4F6F5' },
    { media: '(prefers-color-scheme: dark)', color: '#0E1513' }
  ],
  colorScheme: 'light dark',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={publicSans.className}>{children}</body>
    </html>
  );
}
