import { NextResponse } from 'next/server';
import { MOCK_ALUMNI } from '@/lib/mock-data';

export async function GET() {
  const stage_counts: Record<string, number> = {};
  const sector_counts: Record<string, number> = {};
  for (const a of MOCK_ALUMNI) {
    stage_counts[a.venture_stage] = (stage_counts[a.venture_stage] || 0) + 1;
    sector_counts[a.sector] = (sector_counts[a.sector] || 0) + 1;
  }

  return NextResponse.json({
    alumni: MOCK_ALUMNI,
    stage_counts,
    sector_counts,
    total: MOCK_ALUMNI.length,
  });
}
