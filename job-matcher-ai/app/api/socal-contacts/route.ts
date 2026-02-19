import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

// Comprehensive LA and San Diego MSA cities
const LA_METRO_CITIES = [
  // Los Angeles County
  'Los Angeles', 'Long Beach', 'Santa Monica', 'Pasadena', 'Glendale', 'Burbank',
  'Beverly Hills', 'West Hollywood', 'Culver City', 'Inglewood', 'Torrance',
  'Compton', 'Downey', 'Norwalk', 'Whittier', 'Pomona', 'El Monte', 'West Covina',
  'Arcadia', 'Monrovia', 'Azusa', 'Covina', 'Claremont', 'La Verne', 'Lancaster',
  'Palmdale', 'Santa Clarita', 'Malibu', 'Calabasas', 'Manhattan Beach',
  'Hermosa Beach', 'Redondo Beach', 'El Segundo', 'Hawthorne', 'Gardena',
  'Carson', 'Lakewood', 'Cerritos', 'Paramount', 'Bellflower', 'South Gate',
  'Huntington Park', 'Bell', 'Maywood', 'Vernon', 'Commerce', 'Montebello',
  'Pico Rivera', 'La Mirada', 'Diamond Bar', 'Walnut', 'Rowland Heights',
  'Hacienda Heights', 'La Puente', 'Baldwin Park', 'Duarte', 'Irwindale',
  'San Dimas', 'Glendora', 'San Fernando', 'Palos Verdes', 'Rolling Hills',
  'Rancho Palos Verdes', 'Lomita', 'Harbor City', 'San Pedro', 'Wilmington',
  'Marina del Rey', 'Venice', 'Pacific Palisades', 'Brentwood', 'Westwood',
  'Century City', 'Hollywood', 'Silver Lake', 'Echo Park', 'Los Feliz',
  'Atwater Village', 'Eagle Rock', 'Highland Park', 'South Pasadena',
  'San Marino', 'Alhambra', 'Monterey Park', 'Rosemead', 'Temple City',
  'Altadena', 'Sierra Madre',
  // Orange County
  'Anaheim', 'Irvine', 'Santa Ana', 'Huntington Beach', 'Garden Grove',
  'Orange', 'Fullerton', 'Costa Mesa', 'Mission Viejo', 'Newport Beach',
  'Westminster', 'Buena Park', 'Lake Forest', 'Tustin', 'Yorba Linda',
  'San Clemente', 'Laguna Beach', 'Laguna Niguel', 'Aliso Viejo', 'Dana Point',
  'San Juan Capistrano', 'Rancho Santa Margarita', 'Placentia', 'Brea',
  'La Habra', 'Cypress', 'Los Alamitos', 'Seal Beach', 'Fountain Valley',
  'Stanton', 'La Palma', 'Laguna Hills', 'Laguna Woods', 'Ladera Ranch',
  'Orange County',
  // Ventura County (LA CSA)
  'Thousand Oaks', 'Oxnard', 'Ventura', 'Simi Valley', 'Camarillo',
  'Moorpark', 'Ojai', 'Port Hueneme', 'Fillmore', 'Santa Paula',
  'Westlake Village', 'Agoura Hills', 'Oak Park', 'Newbury Park',
  // Inland Empire (Greater LA)
  'Riverside', 'San Bernardino', 'Ontario', 'Rancho Cucamonga', 'Fontana',
  'Moreno Valley', 'Corona', 'Chino', 'Chino Hills', 'Upland', 'Redlands',
  'Temecula', 'Murrieta', 'Menifee', 'Victorville', 'Hesperia', 'Apple Valley',
  'Loma Linda', 'Rialto', 'Colton', 'Highland', 'Yucaipa', 'Beaumont',
  'Hemet', 'San Jacinto', 'Perris', 'Lake Elsinore', 'Wildomar', 'Eastvale',
  'Jurupa Valley', 'Norco', 'Montclair',
];

const SAN_DIEGO_METRO_CITIES = [
  'San Diego', 'Chula Vista', 'Oceanside', 'Escondido', 'Carlsbad',
  'El Cajon', 'Vista', 'San Marcos', 'Encinitas', 'National City',
  'La Mesa', 'Santee', 'Poway', 'Imperial Beach', 'Coronado',
  'Solana Beach', 'Del Mar', 'La Jolla', 'Rancho Bernardo', 'Rancho Santa Fe',
  'Cardiff', 'Leucadia', 'Fallbrook', 'Bonsall', 'Valley Center',
  'Ramona', 'Alpine', 'Jamul', 'Spring Valley', 'Lemon Grove',
];

const ALL_SOCAL_CITIES = [...LA_METRO_CITIES, ...SAN_DIEGO_METRO_CITIES];

export interface SoCalContact {
  id: number;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  personal_email: string | null;
  work_email: string | null;
  normalized_phone_number: string | null;
  company: string | null;
  position: string | null;
  city: string | null;
  state: string | null;
  location_name: string | null;
  linkedin_url: string | null;
  headline: string | null;
  taxonomy_classification: string | null;
  donor_tier: string | null;
  donor_total_score: number | null;
  joshua_tree_invited: boolean | null;
  joshua_tree_invited_at: string | null;
}

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const search = url.searchParams.get('search') || '';
    const sortBy = url.searchParams.get('sortBy') || 'city';
    const sortOrder = url.searchParams.get('sortOrder') || 'asc';

    // Query contacts by city - using simpler approach
    const { data: cityData, error: cityError } = await supabase
      .from('contacts')
      .select(`
        id,
        first_name,
        last_name,
        email,
        personal_email,
        work_email,
        normalized_phone_number,
        company,
        position,
        city,
        state,
        location_name,
        linkedin_url,
        headline,
        taxonomy_classification,
        donor_tier,
        donor_total_score,
        joshua_tree_invited,
        joshua_tree_invited_at
      `)
      .eq('state', 'California')
      .in('city', ALL_SOCAL_CITIES);

    if (cityError) {
      console.error('City query error:', cityError);
      throw cityError;
    }

    // Separate query for location_name patterns (LA Metro, etc.)
    const { data: metroData, error: metroError } = await supabase
      .from('contacts')
      .select(`
        id,
        first_name,
        last_name,
        email,
        personal_email,
        work_email,
        normalized_phone_number,
        company,
        position,
        city,
        state,
        location_name,
        linkedin_url,
        headline,
        taxonomy_classification,
        donor_tier,
        donor_total_score,
        joshua_tree_invited,
        joshua_tree_invited_at
      `)
      .ilike('location_name', '%Los Angeles Metropolitan%');

    if (metroError) {
      console.error('Metro query error:', metroError);
      // Don't throw, just continue with city data
    }

    // Merge and deduplicate results
    const allContacts = [...(cityData || []), ...(metroData || [])];
    const uniqueContacts = Array.from(
      new Map(allContacts.map(c => [c.id, c])).values()
    );

    // Filter by search term if provided
    let filteredContacts = uniqueContacts;
    if (search) {
      const searchLower = search.toLowerCase();
      filteredContacts = uniqueContacts.filter(contact => {
        const searchableText = [
          contact.first_name,
          contact.last_name,
          contact.company,
          contact.position,
          contact.city,
          contact.headline,
          contact.email,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return searchableText.includes(searchLower);
      });
    }

    // Sort contacts
    filteredContacts.sort((a, b) => {
      let aVal: any = a[sortBy as keyof SoCalContact];
      let bVal: any = b[sortBy as keyof SoCalContact];

      // Handle nulls
      if (aVal === null) aVal = '';
      if (bVal === null) bVal = '';

      // String comparison
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      // Number comparison
      if (sortOrder === 'asc') {
        return (aVal || 0) - (bVal || 0);
      }
      return (bVal || 0) - (aVal || 0);
    });

    // Calculate region counts
    const laMetroCount = filteredContacts.filter(c =>
      LA_METRO_CITIES.includes(c.city || '') ||
      (c.location_name || '').includes('Los Angeles')
    ).length;

    const sanDiegoCount = filteredContacts.filter(c =>
      SAN_DIEGO_METRO_CITIES.includes(c.city || '')
    ).length;

    const invitedCount = filteredContacts.filter(c => c.joshua_tree_invited).length;

    return new Response(JSON.stringify({
      contacts: filteredContacts,
      total: filteredContacts.length,
      regions: {
        la_metro: laMetroCount,
        san_diego: sanDiegoCount,
      },
      invited_count: invitedCount,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error: any) {
    console.error('SoCal contacts API error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// PATCH endpoint to update invitation status
export async function PATCH(req: Request) {
  try {
    const body = await req.json();
    const { contactId, invited } = body;

    if (!contactId) {
      return new Response(JSON.stringify({ error: 'contactId is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const updateData: any = {
      joshua_tree_invited: invited,
    };

    if (invited) {
      updateData.joshua_tree_invited_at = new Date().toISOString();
    } else {
      updateData.joshua_tree_invited_at = null;
    }

    const { data, error } = await supabase
      .from('contacts')
      .update(updateData)
      .eq('id', contactId)
      .select('id, joshua_tree_invited, joshua_tree_invited_at')
      .single();

    if (error) {
      console.error('Update error:', error);
      throw error;
    }

    return new Response(JSON.stringify({ success: true, contact: data }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error: any) {
    console.error('PATCH error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
