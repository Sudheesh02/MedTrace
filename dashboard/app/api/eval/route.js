import { getEval } from '../../../lib/evalreport.js';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const data = getEval();
    return Response.json(data, { status: data.ok ? 200 : 404 });
  } catch (e) {
    return Response.json({ ok: false, error: String(e?.message || e), seeds: [] }, { status: 500 });
  }
}