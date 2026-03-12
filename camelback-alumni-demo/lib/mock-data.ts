// ── Mock Data: 20 Camelback Ventures alumni (13 nonprofit, 7 for-profit) ──

export type VentureStage =
  // For-profit stages
  | 'pre_seed' | 'seed' | 'series_a' | 'series_b_plus' | 'growth' | 'acquired'
  // Nonprofit stages
  | 'startup' | 'developing' | 'established' | 'scaling' | 'merged'
  // Shared
  | 'closed';

export type ActivityLevel = 'very_active' | 'active' | 'moderate' | 'quiet' | 'inactive';
export type Sector = 'edtech' | 'fintech' | 'healthtech' | 'climate' | 'workforce' | 'social_impact' | 'consumer' | 'enterprise_saas' | 'media';
export type VentureType = 'for_profit' | 'nonprofit';

export interface Alumni {
  id: number;
  first_name: string;
  last_name: string;
  cohort: string;
  cohort_year: number;
  venture_name: string;
  venture_role: string;
  venture_type: VentureType;
  sector: Sector;
  venture_stage: VentureStage;
  city: string;
  state: string;
  headline: string;
  linkedin_url?: string;
  // For-profit: capital raised. Nonprofit: total grants received.
  total_funding: number;
  last_funding_date?: string;
  // For-profit: "Series A", "Seed". Nonprofit: "Foundation Grant", "Government Grant".
  last_funding_type?: string;
  // For-profit: "$1M-$2.5M ARR". Nonprofit: "$3.2M annual budget".
  revenue_range?: string;
  team_size: number;
  linkedin_followers: number;
  linkedin_posts_30d: number;
  linkedin_engagement_rate: number;
  last_post_date?: string;
  news_mentions_90d: number;
  last_news_date?: string;
  last_news_headline?: string;
  activity_level: ActivityLevel;
  activity_score: number;
  momentum: 'rising' | 'stable' | 'declining' | 'unknown';
  key_updates: string[];
  risk_flags: string[];
  last_camelback_touchpoint?: string;
  camelback_engagement_score: number;
  scraped_at: string;
  // Nonprofit-specific fields
  people_served?: number;
  impact_metric?: string;
}

export interface AlumniDetail extends Alumni {
  email?: string;
  summary: string;
  linkedin_posts_recent: Array<{
    date: string;
    text: string;
    likes: number;
    comments: number;
    reposts: number;
  }>;
  news_articles: Array<{
    date: string;
    title: string;
    source: string;
    url: string;
    sentiment: 'positive' | 'neutral' | 'negative';
  }>;
  funding_history: Array<{
    date: string;
    type: string;
    amount: number;
    lead_investor?: string;
  }>;
  milestones: Array<{
    date: string;
    description: string;
    type: 'funding' | 'product' | 'team' | 'award' | 'partnership' | 'media';
  }>;
  camelback_notes?: string;
}

// ── Stage config ──────────────────────────────────────────────────────

export const STAGE_CONFIG: Record<VentureStage, { label: string; color: string; bg: string; order: number; group: 'for_profit' | 'nonprofit' | 'shared' }> = {
  // Nonprofit stages
  startup: { label: 'Startup', color: 'text-gray-700 dark:text-gray-300', bg: 'bg-gray-100 border-gray-200 dark:bg-gray-800/40 dark:border-gray-700', order: 1, group: 'nonprofit' },
  developing: { label: 'Developing', color: 'text-teal-700 dark:text-teal-300', bg: 'bg-teal-100 border-teal-200 dark:bg-teal-900/40 dark:border-teal-800', order: 3, group: 'nonprofit' },
  established: { label: 'Established', color: 'text-cyan-700 dark:text-cyan-300', bg: 'bg-cyan-100 border-cyan-200 dark:bg-cyan-900/40 dark:border-cyan-800', order: 5, group: 'nonprofit' },
  scaling: { label: 'Scaling', color: 'text-green-700 dark:text-green-300', bg: 'bg-green-100 border-green-200 dark:bg-green-900/40 dark:border-green-800', order: 9, group: 'nonprofit' },
  merged: { label: 'Merged', color: 'text-amber-700 dark:text-amber-300', bg: 'bg-amber-100 border-amber-200 dark:bg-amber-900/40 dark:border-amber-800', order: 11, group: 'nonprofit' },
  // For-profit stages
  pre_seed: { label: 'Pre-Seed', color: 'text-gray-700 dark:text-gray-300', bg: 'bg-gray-100 border-gray-200 dark:bg-gray-800/40 dark:border-gray-700', order: 2, group: 'for_profit' },
  seed: { label: 'Seed', color: 'text-blue-700 dark:text-blue-300', bg: 'bg-blue-100 border-blue-200 dark:bg-blue-900/40 dark:border-blue-800', order: 4, group: 'for_profit' },
  series_a: { label: 'Series A', color: 'text-indigo-700 dark:text-indigo-300', bg: 'bg-indigo-100 border-indigo-200 dark:bg-indigo-900/40 dark:border-indigo-800', order: 6, group: 'for_profit' },
  series_b_plus: { label: 'Series B+', color: 'text-purple-700 dark:text-purple-300', bg: 'bg-purple-100 border-purple-200 dark:bg-purple-900/40 dark:border-purple-800', order: 8, group: 'for_profit' },
  growth: { label: 'Growth', color: 'text-green-700 dark:text-green-300', bg: 'bg-green-100 border-green-200 dark:bg-green-900/40 dark:border-green-800', order: 10, group: 'for_profit' },
  acquired: { label: 'Acquired', color: 'text-amber-700 dark:text-amber-300', bg: 'bg-amber-100 border-amber-200 dark:bg-amber-900/40 dark:border-amber-800', order: 12, group: 'for_profit' },
  // Shared
  closed: { label: 'Closed', color: 'text-red-700 dark:text-red-300', bg: 'bg-red-100 border-red-200 dark:bg-red-900/40 dark:border-red-800', order: 14, group: 'shared' },
};

export const SECTOR_CONFIG: Record<Sector, { label: string; color: string }> = {
  edtech: { label: 'EdTech', color: 'bg-sky-100 text-sky-700 border-sky-200' },
  fintech: { label: 'FinTech', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  healthtech: { label: 'HealthTech', color: 'bg-rose-100 text-rose-700 border-rose-200' },
  climate: { label: 'Climate', color: 'bg-lime-100 text-lime-700 border-lime-200' },
  workforce: { label: 'Workforce', color: 'bg-orange-100 text-orange-700 border-orange-200' },
  social_impact: { label: 'Social Impact', color: 'bg-violet-100 text-violet-700 border-violet-200' },
  consumer: { label: 'Consumer', color: 'bg-pink-100 text-pink-700 border-pink-200' },
  enterprise_saas: { label: 'Enterprise SaaS', color: 'bg-cyan-100 text-cyan-700 border-cyan-200' },
  media: { label: 'Media', color: 'bg-amber-100 text-amber-700 border-amber-200' },
};

export const ACTIVITY_CONFIG: Record<ActivityLevel, { label: string; color: string }> = {
  very_active: { label: 'Very Active', color: 'text-green-600' },
  active: { label: 'Active', color: 'text-blue-600' },
  moderate: { label: 'Moderate', color: 'text-yellow-600' },
  quiet: { label: 'Quiet', color: 'text-orange-500' },
  inactive: { label: 'Inactive', color: 'text-red-500' },
};

// ── Nonprofit ventures (13) ───────────────────────────────────────────

export const MOCK_ALUMNI: Alumni[] = [
  {
    id: 1, first_name: 'Aisha', last_name: 'Reynolds', cohort: 'Cohort 12', cohort_year: 2022,
    venture_name: 'BridgeEd', venture_role: 'Executive Director & Co-Founder', venture_type: 'nonprofit', sector: 'edtech',
    venture_stage: 'established', city: 'New Orleans', state: 'LA',
    headline: 'AI-powered literacy programs for Title I schools',
    total_funding: 4200000, last_funding_date: '2026-01-15', last_funding_type: 'NewSchools Venture Fund Grant',
    revenue_range: '$3.2M annual budget', team_size: 18,
    linkedin_followers: 8400, linkedin_posts_30d: 6, linkedin_engagement_rate: 4.2,
    last_post_date: '2026-03-04',
    news_mentions_90d: 4, last_news_date: '2026-02-28',
    last_news_headline: 'BridgeEd receives $2M grant to expand AI literacy programs to 200 schools',
    activity_level: 'very_active', activity_score: 95, momentum: 'rising',
    key_updates: ['Received $2M NewSchools grant (Jan 2026)', 'Expanded to 200 schools across 3 states', 'Named to EdTech 50 list'],
    risk_flags: [],
    last_camelback_touchpoint: '2026-02-15', camelback_engagement_score: 92, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 28000,
    impact_metric: '28,000 students across 200 Title I schools, avg 1.5 grade level reading improvement',
  },
  {
    id: 3, first_name: 'Jasmine', last_name: 'Torres', cohort: 'Cohort 14', cohort_year: 2024,
    venture_name: 'Abuelita Health', venture_role: 'Executive Director & Co-Founder', venture_type: 'nonprofit', sector: 'healthtech',
    venture_stage: 'developing', city: 'San Antonio', state: 'TX',
    headline: 'Culturally responsive health programs for Latino communities',
    total_funding: 1800000, last_funding_date: '2025-11-01', last_funding_type: 'Blue Shield Foundation Grant',
    revenue_range: '$1.4M annual budget', team_size: 9,
    linkedin_followers: 4200, linkedin_posts_30d: 8, linkedin_engagement_rate: 5.8,
    last_post_date: '2026-03-05',
    news_mentions_90d: 3, last_news_date: '2026-02-10',
    last_news_headline: 'How Abuelita Health is reimagining healthcare access for Spanish-speaking families',
    activity_level: 'very_active', activity_score: 91, momentum: 'rising',
    key_updates: ['Launched bilingual AI health navigator', '3,500 patients served in Year 1', 'Featured in TechCrunch Latino Founders series'],
    risk_flags: [],
    last_camelback_touchpoint: '2026-03-01', camelback_engagement_score: 95, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 3500,
    impact_metric: '3,500 patients served, 92% retention rate, 40% reduction in ER visits',
  },
  {
    id: 4, first_name: 'Darius', last_name: 'Washington', cohort: 'Cohort 11', cohort_year: 2021,
    venture_name: 'GreenBlock', venture_role: 'Executive Director & Co-Founder', venture_type: 'nonprofit', sector: 'climate',
    venture_stage: 'established', city: 'Detroit', state: 'MI',
    headline: 'Community solar and energy equity for underserved neighborhoods',
    total_funding: 6800000, last_funding_date: '2025-06-15', last_funding_type: 'EPA Environmental Justice Grant',
    revenue_range: '$4.5M annual budget', team_size: 22,
    linkedin_followers: 6100, linkedin_posts_30d: 4, linkedin_engagement_rate: 3.5,
    last_post_date: '2026-02-20',
    news_mentions_90d: 5, last_news_date: '2026-02-18',
    last_news_headline: 'GreenBlock brings community solar to 1,000 Detroit households',
    activity_level: 'active', activity_score: 78, momentum: 'stable',
    key_updates: ['1,000 households connected to community solar', 'EPA Environmental Justice grant awarded', 'Expanded to Cleveland and Milwaukee'],
    risk_flags: ['Federal IRA incentive changes could affect program economics'],
    last_camelback_touchpoint: '2026-01-20', camelback_engagement_score: 75, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 8500,
    impact_metric: '8,500 households connected to community solar, saving avg $800/year on energy bills',
  },
  {
    id: 5, first_name: 'Priya', last_name: 'Patel', cohort: 'Cohort 13', cohort_year: 2023,
    venture_name: 'SkillBridge', venture_role: 'Executive Director & Co-Founder', venture_type: 'nonprofit', sector: 'workforce',
    venture_stage: 'developing', city: 'Oakland', state: 'CA',
    headline: 'Career navigation and mentorship for first-gen college graduates',
    total_funding: 2200000, last_funding_date: '2025-08-10', last_funding_type: 'Lumina Foundation Grant',
    revenue_range: '$1.8M annual budget', team_size: 11,
    linkedin_followers: 5600, linkedin_posts_30d: 5, linkedin_engagement_rate: 4.8,
    last_post_date: '2026-03-03',
    news_mentions_90d: 2, last_news_date: '2026-01-25',
    last_news_headline: 'SkillBridge partners with Year Up for career matching program',
    activity_level: 'active', activity_score: 84, momentum: 'rising',
    key_updates: ['Year Up partnership launched', '2,000 graduates placed in careers', 'Building employer partner network'],
    risk_flags: [],
    last_camelback_touchpoint: '2026-02-28', camelback_engagement_score: 88, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 2000,
    impact_metric: '2,000 first-gen graduates placed in careers, 85% placement rate, $62K avg starting salary',
  },
  {
    id: 8, first_name: 'Jordan', last_name: 'Lee', cohort: 'Cohort 12', cohort_year: 2022,
    venture_name: 'EquiLearn', venture_role: 'Executive Director & Co-Founder', venture_type: 'nonprofit', sector: 'edtech',
    venture_stage: 'developing', city: 'Chicago', state: 'IL',
    headline: 'Personalized math instruction for Black and brown students K-8',
    total_funding: 1500000, last_funding_date: '2025-04-20', last_funding_type: 'Chicago Community Trust Grant',
    revenue_range: '$1.1M annual budget', team_size: 8,
    linkedin_followers: 3200, linkedin_posts_30d: 3, linkedin_engagement_rate: 3.9,
    last_post_date: '2026-02-18',
    news_mentions_90d: 1, last_news_date: '2025-12-15',
    last_news_headline: 'EquiLearn pilot shows 35% improvement in math scores for Chicago students',
    activity_level: 'moderate', activity_score: 62, momentum: 'stable',
    key_updates: ['Pilot results strong (35% improvement)', 'Expanding to 15 schools in CPS', 'Applying for MacArthur Foundation grant'],
    risk_flags: ['Budget may be tight without new grants by Q3'],
    last_camelback_touchpoint: '2026-01-08', camelback_engagement_score: 72, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 2400,
    impact_metric: '2,400 students served, 35% improvement in math proficiency scores',
  },
  {
    id: 9, first_name: 'Tanya', last_name: 'Williams', cohort: 'Cohort 8', cohort_year: 2018,
    venture_name: 'Rooted Kitchen', venture_role: 'Former Executive Director', venture_type: 'nonprofit', sector: 'consumer',
    venture_stage: 'merged', city: 'Baltimore', state: 'MD',
    headline: 'Community meal programs celebrating Black food traditions (merged 2025)',
    total_funding: 3500000, last_funding_date: '2023-06-01', last_funding_type: 'Foundation Grants',
    revenue_range: 'N/A (merged)', team_size: 0,
    linkedin_followers: 9800, linkedin_posts_30d: 1, linkedin_engagement_rate: 1.5,
    last_post_date: '2026-01-30',
    news_mentions_90d: 2, last_news_date: '2026-01-15',
    last_news_headline: 'Tanya Williams joins national food justice alliance after Rooted Kitchen merger',
    activity_level: 'quiet', activity_score: 35, momentum: 'stable',
    key_updates: ['Merged into National Food Justice Alliance (Nov 2025)', 'Tanya joined alliance board', 'Advising two Camelback alumni organizations'],
    risk_flags: [],
    last_camelback_touchpoint: '2025-12-20', camelback_engagement_score: 60, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 12000,
    impact_metric: '12,000 families received culturally relevant meal programs, 85% reported improved nutrition',
  },
  {
    id: 10, first_name: 'Xavier', last_name: 'Green', cohort: 'Cohort 11', cohort_year: 2021,
    venture_name: 'UrbanGrid', venture_role: 'Executive Director & Co-Founder', venture_type: 'nonprofit', sector: 'enterprise_saas',
    venture_stage: 'established', city: 'Washington', state: 'DC',
    headline: 'Civic technology improving municipal services in underserved cities',
    total_funding: 5500000, last_funding_date: '2025-10-01', last_funding_type: 'Knight Foundation Grant',
    revenue_range: '$3.8M annual budget', team_size: 28,
    linkedin_followers: 4800, linkedin_posts_30d: 4, linkedin_engagement_rate: 3.2,
    last_post_date: '2026-02-28',
    news_mentions_90d: 3, last_news_date: '2026-02-10',
    last_news_headline: 'UrbanGrid deploys civic tech platform in City of Newark',
    activity_level: 'active', activity_score: 79, momentum: 'rising',
    key_updates: ['Newark deployment complete', '12 cities served nationwide', 'Bloomberg Philanthropies partnership'],
    risk_flags: ['Government budget cycles create uneven cash flow'],
    last_camelback_touchpoint: '2026-02-05', camelback_engagement_score: 70, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 450000,
    impact_metric: '450,000 residents across 12 cities benefiting from improved municipal services',
  },
  {
    id: 11, first_name: 'Keisha', last_name: 'Adams', cohort: 'Cohort 13', cohort_year: 2023,
    venture_name: 'VentureReady', venture_role: 'Executive Director', venture_type: 'nonprofit', sector: 'social_impact',
    venture_stage: 'developing', city: 'New York', state: 'NY',
    headline: 'Accelerator programs for BIPOC founders at HBCUs',
    total_funding: 2800000, last_funding_date: '2026-01-10', last_funding_type: 'Google.org Grant',
    revenue_range: '$1.2M annual budget', team_size: 7,
    linkedin_followers: 6800, linkedin_posts_30d: 7, linkedin_engagement_rate: 5.5,
    last_post_date: '2026-03-04',
    news_mentions_90d: 2, last_news_date: '2026-02-20',
    last_news_headline: 'VentureReady powers accelerator programs at 5 HBCUs',
    activity_level: 'very_active', activity_score: 87, momentum: 'rising',
    key_updates: ['5 HBCU partnerships live', '120 founders served through programs', 'Google.org Impact Challenge finalist'],
    risk_flags: [],
    last_camelback_touchpoint: '2026-03-02', camelback_engagement_score: 90, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 120,
    impact_metric: '120 founders served, 78% secured follow-on funding',
  },
  {
    id: 12, first_name: 'Rafael', last_name: 'Mendez', cohort: 'Cohort 14', cohort_year: 2024,
    venture_name: 'TierraVerde', venture_role: 'Executive Director & Co-Founder', venture_type: 'nonprofit', sector: 'climate',
    venture_stage: 'startup', city: 'Miami', state: 'FL',
    headline: 'Climate resilience planning for frontline communities',
    total_funding: 850000, last_funding_date: '2025-12-01', last_funding_type: 'FEMA Resilience Grant',
    revenue_range: '$650K annual budget', team_size: 4,
    linkedin_followers: 2100, linkedin_posts_30d: 4, linkedin_engagement_rate: 4.1,
    last_post_date: '2026-02-22',
    news_mentions_90d: 1, last_news_date: '2026-01-05',
    last_news_headline: 'Miami nonprofit TierraVerde maps climate risk for Little Havana residents',
    activity_level: 'moderate', activity_score: 58, momentum: 'stable',
    key_updates: ['Pilot with Miami-Dade County', 'Climate mapping tool in beta', 'FEMA resilience grant awarded'],
    risk_flags: ['Heavy reliance on government grants', 'Board development needed'],
    last_camelback_touchpoint: '2026-01-15', camelback_engagement_score: 65, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 4200,
    impact_metric: '4,200 families reached with climate preparedness resources',
  },
  {
    id: 14, first_name: 'Andre', last_name: 'Mitchell', cohort: 'Cohort 9', cohort_year: 2019,
    venture_name: 'CodePath Academy', venture_role: 'COO', venture_type: 'nonprofit', sector: 'workforce',
    venture_stage: 'scaling', city: 'San Francisco', state: 'CA',
    headline: 'Free technical training and job placement for underrepresented engineers',
    total_funding: 28000000, last_funding_date: '2025-08-01', last_funding_type: 'Multi-year Foundation Grant',
    revenue_range: '$12M annual budget', team_size: 65,
    linkedin_followers: 7500, linkedin_posts_30d: 2, linkedin_engagement_rate: 2.8,
    last_post_date: '2026-02-15',
    news_mentions_90d: 4, last_news_date: '2026-02-05',
    last_news_headline: 'CodePath Academy graduates 5,000th student with 90% placement rate',
    activity_level: 'active', activity_score: 72, momentum: 'stable',
    key_updates: ['5,000th graduate milestone', '90% job placement rate', 'Expanded to 30 university partnerships'],
    risk_flags: ['Tech hiring market fluctuations affect outcomes'],
    last_camelback_touchpoint: '2025-10-30', camelback_engagement_score: 50, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 5000,
    impact_metric: '5,000 graduates with 90% job placement rate, $85K avg starting salary',
  },
  {
    id: 15, first_name: 'Destiny', last_name: 'Harper', cohort: 'Cohort 15', cohort_year: 2025,
    venture_name: 'BrightPath', venture_role: 'Executive Director & Founder', venture_type: 'nonprofit', sector: 'edtech',
    venture_stage: 'startup', city: 'Memphis', state: 'TN',
    headline: 'Parent engagement programs for low-income school districts',
    total_funding: 380000, last_funding_date: '2025-11-15', last_funding_type: 'Walton Family Foundation Grant',
    revenue_range: '$280K annual budget', team_size: 2,
    linkedin_followers: 980, linkedin_posts_30d: 9, linkedin_engagement_rate: 8.1,
    last_post_date: '2026-03-05',
    news_mentions_90d: 0,
    activity_level: 'very_active', activity_score: 85, momentum: 'rising',
    key_updates: ['Pilot with 3 Memphis schools', 'Parent engagement up 40% in pilot', 'Applying for additional foundation grants'],
    risk_flags: ['Very early stage', 'Solo founder risk', 'Grant-dependent budget'],
    last_camelback_touchpoint: '2026-03-05', camelback_engagement_score: 98, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 1500,
    impact_metric: '1,500 families engaged, 40% increase in parent participation',
  },
  {
    id: 17, first_name: 'Simone', last_name: 'Davis', cohort: 'Cohort 7', cohort_year: 2017,
    venture_name: 'VoiceUp', venture_role: 'Former Executive Director', venture_type: 'nonprofit', sector: 'social_impact',
    venture_stage: 'closed', city: 'Chicago', state: 'IL',
    headline: 'Civic engagement and voter registration for underrepresented communities (wound down 2024)',
    total_funding: 3200000, last_funding_type: 'Foundation Grants',
    revenue_range: 'N/A (closed)', team_size: 0,
    linkedin_followers: 5400, linkedin_posts_30d: 1, linkedin_engagement_rate: 1.2,
    last_post_date: '2026-01-10',
    news_mentions_90d: 0,
    activity_level: 'quiet', activity_score: 25, momentum: 'unknown',
    key_updates: ['VoiceUp wound down (Aug 2024)', 'Simone joined Civic Health Alliance as VP', 'Available as mentor to current fellows'],
    risk_flags: [],
    last_camelback_touchpoint: '2025-08-15', camelback_engagement_score: 40, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 85000,
    impact_metric: '85,000 voters registered across 12 cities before closing',
  },
  {
    id: 18, first_name: 'Brandon', last_name: 'Osei', cohort: 'Cohort 14', cohort_year: 2024,
    venture_name: 'FreshRoute', venture_role: 'Executive Director & Co-Founder', venture_type: 'nonprofit', sector: 'consumer',
    venture_stage: 'developing', city: 'Newark', state: 'NJ',
    headline: 'Affordable grocery access for food deserts',
    total_funding: 1100000, last_funding_date: '2025-10-15', last_funding_type: 'Robin Hood Foundation Grant',
    revenue_range: '$850K annual budget', team_size: 12,
    linkedin_followers: 2900, linkedin_posts_30d: 4, linkedin_engagement_rate: 4.5,
    last_post_date: '2026-02-28',
    news_mentions_90d: 2, last_news_date: '2026-02-15',
    last_news_headline: 'FreshRoute partners with SNAP to accept EBT for grocery delivery in food deserts',
    activity_level: 'active', activity_score: 74, momentum: 'rising',
    key_updates: ['SNAP/EBT integration live', 'Serving 2,000 households in Newark', 'Expanding to Trenton and Camden'],
    risk_flags: ['Grocery logistics are operationally heavy', 'Needs diversified funding sources'],
    last_camelback_touchpoint: '2026-02-10', camelback_engagement_score: 78, scraped_at: '2026-03-05T08:00:00Z',
    people_served: 2000,
    impact_metric: '2,000 households receiving affordable groceries, avg 35% savings vs corner stores',
  },

  // ── For-profit ventures (7) ─────────────────────────────────────────

  {
    id: 2, first_name: 'Marcus', last_name: 'Johnson', cohort: 'Cohort 10', cohort_year: 2020,
    venture_name: 'PayForward', venture_role: 'CEO & Founder', venture_type: 'for_profit', sector: 'fintech',
    venture_stage: 'series_b_plus', city: 'Atlanta', state: 'GA',
    headline: 'Income share agreements for workforce training programs',
    total_funding: 18500000, last_funding_date: '2025-09-20', last_funding_type: 'Series B',
    revenue_range: '$5M-$10M ARR', team_size: 45,
    linkedin_followers: 12300, linkedin_posts_30d: 3, linkedin_engagement_rate: 3.1,
    last_post_date: '2026-02-25',
    news_mentions_90d: 6, last_news_date: '2026-03-01',
    last_news_headline: 'PayForward partners with three community colleges to pilot new ISA model',
    activity_level: 'active', activity_score: 82, momentum: 'stable',
    key_updates: ['3 community college partnerships signed', 'Hired VP of Engineering from Stripe', '10,000+ students funded to date'],
    risk_flags: ['ISA regulatory environment shifting in some states'],
    last_camelback_touchpoint: '2025-12-10', camelback_engagement_score: 68, scraped_at: '2026-03-05T08:00:00Z',
  },
  {
    id: 6, first_name: 'DeAndre', last_name: 'Brooks', cohort: 'Cohort 9', cohort_year: 2019,
    venture_name: 'CultureShift Media', venture_role: 'CEO & Founder', venture_type: 'for_profit', sector: 'media',
    venture_stage: 'growth', city: 'Los Angeles', state: 'CA',
    headline: 'Multicultural content studio and distribution platform',
    total_funding: 12000000, last_funding_date: '2024-11-01', last_funding_type: 'Series A',
    revenue_range: '$5M-$10M ARR', team_size: 35,
    linkedin_followers: 15200, linkedin_posts_30d: 2, linkedin_engagement_rate: 2.1,
    last_post_date: '2026-02-12',
    news_mentions_90d: 8, last_news_date: '2026-03-02',
    last_news_headline: 'CultureShift Media signs distribution deal with Paramount+',
    activity_level: 'active', activity_score: 76, momentum: 'stable',
    key_updates: ['Paramount+ distribution deal signed', 'Original content library at 200+ hours', 'Profitability target: Q4 2026'],
    risk_flags: ['Content studio economics are capital-intensive'],
    last_camelback_touchpoint: '2025-11-15', camelback_engagement_score: 55, scraped_at: '2026-03-05T08:00:00Z',
  },
  {
    id: 7, first_name: 'Camille', last_name: 'Okafor', cohort: 'Cohort 15', cohort_year: 2025,
    venture_name: 'NestEgg', venture_role: 'CEO & Founder', venture_type: 'for_profit', sector: 'fintech',
    venture_stage: 'pre_seed', city: 'Philadelphia', state: 'PA',
    headline: 'Micro-savings and financial wellness for hourly workers',
    total_funding: 350000, last_funding_date: '2025-12-01', last_funding_type: 'Pre-Seed',
    revenue_range: '<$100K', team_size: 3,
    linkedin_followers: 1800, linkedin_posts_30d: 10, linkedin_engagement_rate: 7.2,
    last_post_date: '2026-03-05',
    news_mentions_90d: 1, last_news_date: '2026-01-10',
    last_news_headline: 'Camelback Ventures fellow launches NestEgg to help hourly workers save',
    activity_level: 'very_active', activity_score: 88, momentum: 'rising',
    key_updates: ['Launched beta with 500 users', 'Accepted into Techstars Social Impact', 'Building employer partnerships'],
    risk_flags: ['Very early stage', 'Will need seed round by Q3 2026'],
    last_camelback_touchpoint: '2026-03-04', camelback_engagement_score: 96, scraped_at: '2026-03-05T08:00:00Z',
  },
  {
    id: 13, first_name: 'Monique', last_name: 'Baptiste', cohort: 'Cohort 10', cohort_year: 2020,
    venture_name: 'HealSpace', venture_role: 'CEO & Founder', venture_type: 'for_profit', sector: 'healthtech',
    venture_stage: 'series_a', city: 'Houston', state: 'TX',
    headline: 'Mental health platform for Black women and femmes',
    total_funding: 3800000, last_funding_date: '2025-05-01', last_funding_type: 'Series A',
    revenue_range: '$1M-$2.5M ARR', team_size: 16,
    linkedin_followers: 11200, linkedin_posts_30d: 5, linkedin_engagement_rate: 6.3,
    last_post_date: '2026-03-03',
    news_mentions_90d: 5, last_news_date: '2026-02-25',
    last_news_headline: 'HealSpace reaches 25,000 users, launches employer wellness partnerships',
    activity_level: 'very_active', activity_score: 90, momentum: 'rising',
    key_updates: ['25,000 users on platform', 'Employer wellness product launched', 'Essence magazine feature'],
    risk_flags: [],
    last_camelback_touchpoint: '2026-02-20', camelback_engagement_score: 85, scraped_at: '2026-03-05T08:00:00Z',
  },
  {
    id: 16, first_name: 'Omar', last_name: 'Hussain', cohort: 'Cohort 12', cohort_year: 2022,
    venture_name: 'Halal Capital', venture_role: 'CEO & Co-Founder', venture_type: 'for_profit', sector: 'fintech',
    venture_stage: 'seed', city: 'Minneapolis', state: 'MN',
    headline: 'Sharia-compliant investing platform for American Muslims',
    total_funding: 1600000, last_funding_date: '2025-06-01', last_funding_type: 'Seed',
    revenue_range: '$500K-$1M ARR', team_size: 10,
    linkedin_followers: 3800, linkedin_posts_30d: 3, linkedin_engagement_rate: 3.4,
    last_post_date: '2026-02-20',
    news_mentions_90d: 2, last_news_date: '2026-02-01',
    last_news_headline: 'Halal Capital crosses $50M in assets under management',
    activity_level: 'moderate', activity_score: 65, momentum: 'stable',
    key_updates: ['$50M AUM milestone', '8,000 active investors', 'Launched retirement accounts'],
    risk_flags: ['Regulatory compliance costs for financial products'],
    last_camelback_touchpoint: '2025-12-05', camelback_engagement_score: 58, scraped_at: '2026-03-05T08:00:00Z',
  },
  {
    id: 19, first_name: 'Maya', last_name: 'Chen-Ramirez', cohort: 'Cohort 16', cohort_year: 2026,
    venture_name: 'Kindora', venture_role: 'CTO & Co-Founder', venture_type: 'for_profit', sector: 'enterprise_saas',
    venture_stage: 'pre_seed', city: 'Oakland', state: 'CA',
    headline: 'AI-powered grant intelligence for under-resourced nonprofits',
    total_funding: 0, last_funding_type: 'Bootstrapped',
    revenue_range: '<$100K', team_size: 2,
    linkedin_followers: 6100, linkedin_posts_30d: 8, linkedin_engagement_rate: 6.8,
    last_post_date: '2026-03-06',
    news_mentions_90d: 1, last_news_date: '2026-02-20',
    last_news_headline: 'Oakland startup Kindora uses AI to help small nonprofits find grant funding',
    activity_level: 'very_active', activity_score: 93, momentum: 'rising',
    key_updates: ['Closing first enterprise deal', 'Production platform live with paying customers', 'Camelback Cohort 16 fellow'],
    risk_flags: ['Pre-revenue enterprise model', 'Bootstrapped, no outside capital yet'],
    last_camelback_touchpoint: '2026-03-06', camelback_engagement_score: 99, scraped_at: '2026-03-05T08:00:00Z',
  },
  {
    id: 20, first_name: 'Troy', last_name: 'Richardson', cohort: 'Cohort 8', cohort_year: 2018,
    venture_name: 'EmpowerHR', venture_role: 'CEO & Founder', venture_type: 'for_profit', sector: 'enterprise_saas',
    venture_stage: 'growth', city: 'Dallas', state: 'TX',
    headline: 'DEI analytics and retention platform for enterprise HR',
    total_funding: 15000000, last_funding_date: '2024-08-01', last_funding_type: 'Series B',
    revenue_range: '$5M-$10M ARR', team_size: 42,
    linkedin_followers: 8900, linkedin_posts_30d: 2, linkedin_engagement_rate: 2.4,
    last_post_date: '2026-02-10',
    news_mentions_90d: 3, last_news_date: '2026-01-28',
    last_news_headline: 'EmpowerHR adds AI-driven retention risk scoring to platform',
    activity_level: 'moderate', activity_score: 60, momentum: 'declining',
    key_updates: ['AI retention scoring launched', '200+ enterprise clients', 'DEI budget cuts affecting some customer renewals'],
    risk_flags: ['DEI backlash impacting enterprise budgets', 'Some client churn in conservative markets'],
    last_camelback_touchpoint: '2025-09-20', camelback_engagement_score: 42, scraped_at: '2026-03-05T08:00:00Z',
  },
];

// ── Detail data for expanded views ──────────────────────────────────────

const detailExtensions: Record<number, Partial<AlumniDetail>> = {
  1: {
    email: 'aisha@bridgeed.org',
    summary: 'Aisha is a former teacher who founded BridgeEd after 7 years teaching 3rd grade in New Orleans East. She saw firsthand how technology could personalize literacy instruction for students reading below grade level, and built the organization to bring that to every Title I school.',
    linkedin_posts_recent: [
      { date: '2026-03-04', text: 'We just crossed 200 schools using BridgeEd. Two years ago it was just me and a laptop in a classroom. Grateful for this team and every teacher who believed in what we were building.', likes: 342, comments: 48, reposts: 23 },
      { date: '2026-02-25', text: 'This NewSchools grant means we can reach 100 more schools this year. Every child deserves a reading tutor who never gives up on them.', likes: 289, comments: 31, reposts: 18 },
    ],
    news_articles: [
      { date: '2026-02-28', title: 'BridgeEd receives $2M grant to expand AI literacy programs to 200 schools', source: 'EdSurge', url: '#', sentiment: 'positive' },
      { date: '2026-01-15', title: 'AI in the classroom: How BridgeEd personalizes reading instruction', source: 'Education Week', url: '#', sentiment: 'positive' },
    ],
    funding_history: [
      { date: '2026-01-15', type: 'NewSchools Venture Fund Grant', amount: 2000000 },
      { date: '2024-06-01', type: 'KIPP Foundation Grant', amount: 1200000 },
      { date: '2023-03-01', type: 'Seed Grant', amount: 1000000 },
    ],
    milestones: [
      { date: '2026-02-28', description: 'Named to EdTech 50 list', type: 'award' },
      { date: '2026-01-15', description: 'Received $2M NewSchools Venture Fund grant', type: 'funding' },
      { date: '2025-09-01', description: 'Expanded to Louisiana, Mississippi, and Alabama', type: 'product' },
      { date: '2025-06-01', description: 'Hired Director of Programs from Khan Academy', type: 'team' },
    ],
    camelback_notes: 'One of our strongest alumni. Aisha is a natural leader and has been mentoring Cohort 15 and 16 fellows. She credits Camelback for helping her think about scaling impact without losing mission focus.',
  },
  3: {
    email: 'jasmine@abuelitahealth.org',
    summary: 'Jasmine founded Abuelita Health after her grandmother was misdiagnosed due to a language barrier at a San Antonio hospital. The organization provides bilingual health programs, culturally trained community health workers, and an AI health navigator that speaks Spanish natively.',
    linkedin_posts_recent: [
      { date: '2026-03-05', text: 'Today we launched our AI health navigator in Spanish. My abuelita can now describe her symptoms in her own words and get matched to the right care. This is why we build.', likes: 512, comments: 67, reposts: 45 },
      { date: '2026-02-20', text: '3,500 patients served. Every single one deserves healthcare that respects their language and culture.', likes: 388, comments: 42, reposts: 28 },
    ],
    news_articles: [
      { date: '2026-02-10', title: 'How Abuelita Health is reimagining healthcare access for Spanish-speaking families', source: 'TechCrunch', url: '#', sentiment: 'positive' },
      { date: '2025-12-05', title: 'Latino community health leaders to watch in 2026', source: 'Forbes', url: '#', sentiment: 'positive' },
    ],
    funding_history: [
      { date: '2025-11-01', type: 'Blue Shield Foundation Grant', amount: 1000000 },
      { date: '2024-09-01', type: 'Kresge Foundation Grant', amount: 500000 },
      { date: '2024-03-01', type: 'Community Foundation Grant', amount: 300000 },
    ],
    milestones: [
      { date: '2026-03-05', description: 'Launched bilingual AI health navigator', type: 'product' },
      { date: '2026-02-10', description: 'Featured in TechCrunch Latino Founders series', type: 'media' },
      { date: '2025-11-01', description: 'Received $1M Blue Shield Foundation grant', type: 'funding' },
      { date: '2025-06-01', description: 'Partnership with San Antonio Metro Health', type: 'partnership' },
    ],
    camelback_notes: 'Jasmine is deeply mission-driven and has excellent founder-community fit. Her personal story resonates with funders and press. Watch for expansion to Houston and Dallas in 2027.',
  },
  11: {
    email: 'keisha@ventureready.org',
    summary: 'Keisha launched VentureReady after running accelerator programs at two HBCUs and realizing there was no infrastructure for scaling founder support at historically Black institutions. The organization provides turnkey accelerator programs that HBCUs can adopt with minimal overhead.',
    linkedin_posts_recent: [
      { date: '2026-03-04', text: 'Our 5th HBCU partner just launched their first cohort. 120 founders served and counting. The pipeline of Black entrepreneurial talent is not the problem. Access is.', likes: 478, comments: 56, reposts: 34 },
      { date: '2026-02-15', text: 'Honored to be a Google.org Impact Challenge finalist. This funding would let us reach 10 more HBCUs by 2027.', likes: 312, comments: 38, reposts: 22 },
    ],
    news_articles: [
      { date: '2026-02-20', title: 'VentureReady powers accelerator programs at 5 HBCUs', source: 'Forbes', url: '#', sentiment: 'positive' },
      { date: '2025-11-15', title: 'How one nonprofit is building the founder pipeline at HBCUs', source: 'Fast Company', url: '#', sentiment: 'positive' },
    ],
    funding_history: [
      { date: '2026-01-10', type: 'Google.org Grant', amount: 1500000 },
      { date: '2025-07-15', type: 'Kauffman Foundation Grant', amount: 800000 },
      { date: '2024-03-01', type: 'Startup Grant', amount: 500000 },
    ],
    milestones: [
      { date: '2026-02-20', description: 'Google.org Impact Challenge finalist', type: 'award' },
      { date: '2026-01-10', description: 'Received $1.5M Google.org grant', type: 'funding' },
      { date: '2025-09-01', description: 'Expanded to 5 HBCU partnerships', type: 'partnership' },
      { date: '2025-03-01', description: '78% of alumni founders secured follow-on funding', type: 'product' },
    ],
    camelback_notes: 'Keisha is building exactly the infrastructure the ecosystem needs. Strong board, clear impact metrics. Would benefit from introductions to more corporate funders.',
  },
  14: {
    email: 'andre@codepathacademy.org',
    summary: 'Andre joined CodePath Academy as COO after a decade in tech workforce development. The nonprofit provides free, industry-relevant technical courses at universities, with a focus on increasing the representation of Black, Latino, and Native American engineers in the tech workforce.',
    linkedin_posts_recent: [
      { date: '2026-02-15', text: '5,000 graduates. 90% placed in tech roles. $85K average starting salary. This is what happens when you invest in talent that the industry keeps overlooking.', likes: 892, comments: 94, reposts: 67 },
      { date: '2026-01-20', text: 'Just wrapped our winter cohort at 30 universities. 1,200 students completed the program. The demand is massive.', likes: 445, comments: 52, reposts: 31 },
    ],
    news_articles: [
      { date: '2026-02-05', title: 'CodePath Academy graduates 5,000th student with 90% placement rate', source: 'TechCrunch', url: '#', sentiment: 'positive' },
      { date: '2025-10-15', title: 'Major foundation commits $10M to CodePath expansion', source: 'Inside Higher Ed', url: '#', sentiment: 'positive' },
    ],
    funding_history: [
      { date: '2025-08-01', type: 'Multi-year Foundation Grant', amount: 10000000 },
      { date: '2024-03-01', type: 'Corporate Sponsorships', amount: 8000000 },
      { date: '2023-01-01', type: 'Foundation Grants', amount: 6000000 },
      { date: '2021-06-01', type: 'Initial Grants', amount: 4000000 },
    ],
    milestones: [
      { date: '2026-02-05', description: 'Graduated 5,000th student', type: 'product' },
      { date: '2025-08-01', description: 'Received $10M multi-year foundation grant', type: 'funding' },
      { date: '2025-01-01', description: 'Expanded to 30 university partnerships', type: 'partnership' },
      { date: '2024-09-01', description: 'Launched advanced AI/ML curriculum', type: 'product' },
    ],
    camelback_notes: 'CodePath is one of the most impactful organizations in our alumni portfolio. Andre has been instrumental in scaling operations. Consider featuring in annual impact report.',
  },
};

function getDefaultDetail(alumni: Alumni): AlumniDetail {
  return {
    ...alumni,
    summary: `${alumni.first_name} is the ${alumni.venture_role} of ${alumni.venture_name}, based in ${alumni.city}, ${alumni.state}.`,
    linkedin_posts_recent: [],
    news_articles: alumni.last_news_headline ? [{ date: alumni.last_news_date || '', title: alumni.last_news_headline, source: 'News', url: '#', sentiment: 'positive' as const }] : [],
    funding_history: alumni.total_funding > 0 && alumni.last_funding_date ? [{ date: alumni.last_funding_date, type: alumni.last_funding_type || 'Unknown', amount: alumni.total_funding }] : [],
    milestones: alumni.key_updates.map((u, i) => ({ date: '2026-01-01', description: u, type: 'product' as const })),
  };
}

export function getAlumniDetail(id: number): AlumniDetail | null {
  const alumni = MOCK_ALUMNI.find((a) => a.id === id);
  if (!alumni) return null;
  const base = getDefaultDetail(alumni);
  const ext = detailExtensions[id];
  return ext ? { ...base, ...ext } : base;
}
