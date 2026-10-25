import './globals.css';

export const metadata = {
  title: 'MedTrace | Stock-integrity triage for essential medicines',
  description: 'Alerts, Investigator vs Skeptic verdicts, decision traces and memory evidence from MedTrace runs. Inventory data is simulated.',
  applicationName: 'MedTrace',
  icons: { icon: '/icon.svg', apple: '/icon.svg' },
};

export const viewport = {
  themeColor: '#090d12',
  colorScheme: 'dark',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}