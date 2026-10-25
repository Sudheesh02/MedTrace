import { backendHealth } from '../../../lib/backend.js';

export const dynamic = 'force-dynamic';

export async function GET() {
  return Response.json(await backendHealth());
}