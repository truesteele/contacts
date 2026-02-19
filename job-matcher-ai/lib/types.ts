// ── Network Copilot Types ────────────────────────────────────────────

export interface FilterState {
  proximity_min?: number;
  proximity_tiers?: string[];
  capacity_min?: number;
  capacity_tiers?: string[];
  outdoorithm_fit?: string[];
  kindora_type?: string[];
  company_keyword?: string;
  name_search?: string;
  location_state?: string;
  semantic_query?: string;
  sort_by?: 'proximity' | 'capacity' | 'name' | 'company';
  sort_order?: 'asc' | 'desc';
  limit?: number;
}

export interface ProspectList {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  member_count?: number;
}

export interface ProspectListMember {
  id: string;
  list_id: string;
  contact_id: number;
  outreach_status: 'not_contacted' | 'reached_out' | 'responded' | 'meeting_scheduled' | 'committed' | 'declined';
  notes?: string;
  added_at: string;
}

export interface OutreachDraft {
  id: string;
  list_id?: string;
  contact_id: number;
  subject: string;
  body: string;
  tone: 'warm_professional' | 'formal' | 'casual' | 'networking' | 'fundraising';
  status: 'draft' | 'sent' | 'failed';
  sent_at?: string;
  created_at: string;
}
