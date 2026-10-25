import { getAlerts } from '../../../lib/triage.js';

export const dynamic = 'force-dynamic';

export async function GET(request) {
  const force = new URL(request.url).searchParams.get('refresh') === '1';
  try {
    const data = await getAlerts({ force });
    return Response.json(data, { status: data.ok ? 200 : 503 });
  } catch (e) {
    return Response.json({ ok: false, error: String(e?.message || e), items: [] }, { status: 500 });
  }
}