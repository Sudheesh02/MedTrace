import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  poweredByHeader: false,
  turbopack: { root: here },
  // The API routes read files at runtime; make sure the demo data bundle ships with the serverless functions.
  outputFileTracingIncludes: { '/api/**/*': ['./data-bundle/**/*'] },
};
export default nextConfig;