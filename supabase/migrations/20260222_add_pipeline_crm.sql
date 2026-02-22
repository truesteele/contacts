-- Pipeline CRM: pipelines and deals tables
-- Supports Kanban board for tracking outreach/deals across business entities

-- Pipelines table
CREATE TABLE IF NOT EXISTS pipelines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  slug text UNIQUE NOT NULL,
  entity text NOT NULL,  -- 'kindora', 'outdoorithm', 'truesteele'
  stages jsonb NOT NULL DEFAULT '[
    {"name": "Backlog", "color": "#6B7280"},
    {"name": "Reached Out", "color": "#3B82F6"},
    {"name": "Engaged", "color": "#8B5CF6"},
    {"name": "Proposal", "color": "#F59E0B"},
    {"name": "Negotiating", "color": "#F97316"},
    {"name": "Won", "color": "#10B981"},
    {"name": "Lost", "color": "#EF4444"}
  ]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Deals table
CREATE TABLE IF NOT EXISTS deals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  pipeline_id uuid NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
  contact_id integer REFERENCES contacts(id),
  title text NOT NULL,
  stage text NOT NULL DEFAULT 'backlog',
  amount numeric(12,2),
  close_date date,
  notes text,
  next_action text,
  next_action_date date,
  source text,
  lost_reason text,
  position integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_deals_pipeline_stage ON deals(pipeline_id, stage);
CREATE INDEX idx_deals_contact_id ON deals(contact_id);

-- Seed default pipelines
INSERT INTO pipelines (name, slug, entity) VALUES
  ('Kindora Fundraising', 'kindora-fundraising', 'kindora'),
  ('Outdoorithm Partnerships', 'outdoorithm-partnerships', 'outdoorithm'),
  ('True Steele Consulting', 'truesteele-consulting', 'truesteele');
