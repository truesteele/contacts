/**
 * Metro area definitions for intelligent geographic matching
 * Maps job locations to broader metro areas that should be considered
 */

export interface MetroArea {
  name: string;
  cities: string[];
  states?: string[];
  description?: string;
}

export const METRO_AREAS: Record<string, MetroArea> = {
  'san-francisco-bay-area': {
    name: 'San Francisco Bay Area',
    cities: [
      // San Francisco Peninsula
      'San Francisco', 'Daly City', 'South San Francisco', 'San Bruno',
      'Millbrae', 'Burlingame', 'San Mateo', 'Belmont', 'San Carlos',
      'Redwood City', 'Menlo Park', 'Palo Alto', 'Mountain View',
      'Sunnyvale', 'Santa Clara', 'San Jose', 'Cupertino', 'Saratoga',
      'Los Gatos', 'Campbell', 'Milpitas',

      // East Bay
      'Oakland', 'Berkeley', 'Alameda', 'Emeryville', 'Albany',
      'El Cerrito', 'Richmond', 'San Leandro', 'Hayward', 'Fremont',
      'Union City', 'Newark', 'Pleasanton', 'Livermore', 'Dublin',
      'San Ramon', 'Danville', 'Walnut Creek', 'Concord', 'Martinez',

      // North Bay
      'San Rafael', 'Novato', 'Petaluma', 'Santa Rosa', 'Napa',
      'Vallejo', 'Fairfield', 'Benicia',

      // South Bay
      'Morgan Hill', 'Gilroy', 'Los Altos', 'Los Altos Hills',
      'Atherton', 'Portola Valley', 'Woodside',
    ],
    states: ['California', 'CA'],
    description: 'San Francisco Bay Area including SF, Peninsula, East Bay, South Bay, and North Bay',
  },

  'seattle-metro': {
    name: 'Seattle Metropolitan Area',
    cities: [
      // Seattle Core
      'Seattle', 'Bellevue', 'Redmond', 'Kirkland', 'Bothell',
      'Sammamish', 'Issaquah', 'Mercer Island', 'Medina', 'Clyde Hill',

      // North
      'Shoreline', 'Lake Forest Park', 'Kenmore', 'Woodinville',
      'Edmonds', 'Lynnwood', 'Mountlake Terrace', 'Everett',

      // South
      'Renton', 'Tukwila', 'SeaTac', 'Burien', 'Des Moines',
      'Federal Way', 'Kent', 'Auburn', 'Tacoma',

      // East
      'Newcastle', 'Snoqualmie', 'North Bend', 'Fall City',

      // West
      'Bainbridge Island', 'Bremerton', 'Poulsbo',
    ],
    states: ['Washington', 'WA'],
    description: 'Seattle-Tacoma-Bellevue metropolitan area',
  },

  'portland-metro': {
    name: 'Portland Metropolitan Area',
    cities: [
      // Portland Core
      'Portland',

      // West Side
      'Beaverton', 'Hillsboro', 'Tigard', 'Tualatin', 'Lake Oswego',
      'West Linn', 'Oregon City', 'Wilsonville', 'Sherwood',

      // East Side
      'Gresham', 'Troutdale', 'Wood Village', 'Fairview',

      // North
      'Vancouver', 'Camas', 'Washougal',

      // South
      'Milwaukie', 'Gladstone', 'Canby',
    ],
    states: ['Oregon', 'OR', 'Washington', 'WA'],
    description: 'Portland-Vancouver metropolitan area',
  },

  'new-york-metro': {
    name: 'New York Metropolitan Area',
    cities: [
      // NYC
      'New York', 'Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island',

      // Westchester
      'White Plains', 'Yonkers', 'New Rochelle', 'Mount Vernon',

      // Long Island
      'Hempstead', 'Garden City', 'Great Neck', 'Port Washington',

      // New Jersey
      'Jersey City', 'Hoboken', 'Newark', 'Weehawken', 'Fort Lee',
      'Englewood', 'Teaneck', 'Hackensack', 'Paramus',

      // Connecticut
      'Stamford', 'Greenwich', 'Norwalk', 'Bridgeport',
    ],
    states: ['New York', 'NY', 'New Jersey', 'NJ', 'Connecticut', 'CT'],
    description: 'New York City metropolitan area',
  },

  'boston-metro': {
    name: 'Boston Metropolitan Area',
    cities: [
      'Boston', 'Cambridge', 'Somerville', 'Brookline', 'Newton',
      'Waltham', 'Watertown', 'Arlington', 'Belmont', 'Lexington',
      'Burlington', 'Woburn', 'Quincy', 'Milton', 'Dedham',
      'Needham', 'Wellesley', 'Framingham', 'Natick',
    ],
    states: ['Massachusetts', 'MA'],
    description: 'Greater Boston area',
  },

  'washington-dc-metro': {
    name: 'Washington DC Metropolitan Area',
    cities: [
      // DC
      'Washington',

      // Maryland
      'Bethesda', 'Rockville', 'Silver Spring', 'Gaithersburg',
      'College Park', 'Hyattsville', 'Greenbelt',

      // Virginia
      'Arlington', 'Alexandria', 'Falls Church', 'Fairfax',
      'Tysons', 'McLean', 'Reston', 'Herndon', 'Vienna',
      'Annandale', 'Springfield', 'Woodbridge',
    ],
    states: ['District of Columbia', 'DC', 'Maryland', 'MD', 'Virginia', 'VA'],
    description: 'Washington DC metropolitan area',
  },

  'los-angeles-metro': {
    name: 'Los Angeles Metropolitan Area',
    cities: [
      'Los Angeles', 'Santa Monica', 'Beverly Hills', 'West Hollywood',
      'Culver City', 'Pasadena', 'Glendale', 'Burbank', 'Inglewood',
      'Torrance', 'Redondo Beach', 'Manhattan Beach', 'El Segundo',
      'Long Beach', 'Irvine', 'Anaheim', 'Santa Ana', 'Costa Mesa',
    ],
    states: ['California', 'CA'],
    description: 'Greater Los Angeles area',
  },

  'chicago-metro': {
    name: 'Chicago Metropolitan Area',
    cities: [
      'Chicago', 'Evanston', 'Skokie', 'Oak Park', 'Naperville',
      'Aurora', 'Joliet', 'Schaumburg', 'Elgin', 'Waukegan',
    ],
    states: ['Illinois', 'IL'],
    description: 'Greater Chicago area',
  },
};

/**
 * Expands a list of cities to include all cities in their metro areas
 */
export function expandToMetroAreas(cities: string[]): string[] {
  const expandedCities = new Set<string>(cities);

  // For each input city, check if it's part of a metro area
  for (const city of cities) {
    const cityLower = city.toLowerCase();

    // Find which metro area(s) this city belongs to
    for (const metroArea of Object.values(METRO_AREAS)) {
      const isInMetro = metroArea.cities.some(
        metroCity => metroCity.toLowerCase() === cityLower
      );

      if (isInMetro) {
        // Add all cities from this metro area
        metroArea.cities.forEach(c => expandedCities.add(c));
      }
    }
  }

  return Array.from(expandedCities);
}

/**
 * Gets the metro area name for a city
 */
export function getMetroAreaName(city: string): string | null {
  const cityLower = city.toLowerCase();

  for (const [key, metroArea] of Object.entries(METRO_AREAS)) {
    const isInMetro = metroArea.cities.some(
      metroCity => metroCity.toLowerCase() === cityLower
    );

    if (isInMetro) {
      return metroArea.name;
    }
  }

  return null;
}

/**
 * Gets all cities in a metro area by name or key city
 */
export function getMetroCities(location: string): string[] {
  const locationLower = location.toLowerCase();

  // Check if it's a metro area name
  for (const metroArea of Object.values(METRO_AREAS)) {
    if (metroArea.name.toLowerCase() === locationLower) {
      return metroArea.cities;
    }
  }

  // Check if it's a city within a metro area
  for (const metroArea of Object.values(METRO_AREAS)) {
    const isInMetro = metroArea.cities.some(
      city => city.toLowerCase() === locationLower
    );

    if (isInMetro) {
      return metroArea.cities;
    }
  }

  // Not in any metro area, return just the location
  return [location];
}

/**
 * Best practice commute definitions based on industry standards
 * Source: LinkedIn uses 100mi default, job boards use 25mi, average commute 15-45min
 */
export const COMMUTE_STANDARDS = {
  // LinkedIn Recruiter standard
  METRO_AREA_RADIUS_MILES: 100,

  // Job board standard (Indeed, etc.)
  DEFAULT_SEARCH_RADIUS_MILES: 25,

  // Tight commute for urban areas
  URBAN_COMMUTE_MILES: 10,

  // Extended commute for suburban areas
  SUBURBAN_COMMUTE_MILES: 50,

  // Average commute times
  AVERAGE_COMMUTE_MINUTES: 30,
  MIN_COMMUTE_MINUTES: 15,
  MAX_COMMUTE_MINUTES: 45,
};

/**
 * Get recommended search strategy explanation
 */
export function getSearchStrategyExplanation(jobLocation: string): string {
  const metroName = getMetroAreaName(jobLocation);

  if (metroName) {
    return `Searching entire ${metroName} (~100 mile radius, industry standard). This includes all cities within commutable distance, matching LinkedIn Recruiter and modern ATS best practices.`;
  }

  return `Searching ${jobLocation} and surrounding areas within typical commute distance (25-50 miles).`;
}
