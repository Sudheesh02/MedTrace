import { getMemoryComparison } from '../../../lib/memory.js';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const data = getMemoryComparison();
    return Response.json(data, { status: data.ok ? 200 : 404 });
  } catch (e) {
    return Response.json({ ok: false, reason: String(e?.message || e) }, { status: 500 });
  }
}