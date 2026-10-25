import './globals.css';

export const metadata = {
  title: 'MedTrace Dashboard',
  description: 'Alerts, Investigator vs Skeptic verdicts, traces and memory evidence from MedTrace runs.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}