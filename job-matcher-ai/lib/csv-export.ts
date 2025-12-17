/**
 * CSV Export functionality for candidate data
 * Converts candidate search results to downloadable CSV format
 */

import { Contact } from './supabase';

/**
 * Convert array of contacts to CSV string
 * @param contacts - Array of contact objects
 * @param includeEnrichmentData - Whether to include enriched fields
 * @returns CSV string
 */
export function contactsToCSV(contacts: Contact[], includeEnrichmentData: boolean = true): string {
  if (contacts.length === 0) {
    return 'No contacts to export';
  }

  // Define basic columns
  const basicColumns = [
    'first_name',
    'last_name',
    'email',
    'linkedin_url',
    'company',
    'position',
    'city',
    'state',
    'headline',
  ];

  // Define enrichment columns (if available)
  const enrichmentColumns = includeEnrichmentData ? [
    'enrich_current_company',
    'enrich_current_title',
    'enrich_years_in_current_role',
    'enrich_total_experience_years',
    'enrich_number_of_positions',
    'enrich_number_of_companies',
    'enrich_highest_degree',
    'enrich_follower_count',
    'enrich_connections',
  ] : [];

  const columns = [...basicColumns, ...enrichmentColumns];

  // Build CSV header
  const header = columns.map(escapeCSVValue).join(',');

  // Build CSV rows
  const rows = contacts.map(contact => {
    return columns.map(col => {
      const value = (contact as any)[col];

      // Handle arrays (join with semicolon)
      if (Array.isArray(value)) {
        return escapeCSVValue(value.join('; '));
      }

      // Handle null/undefined
      if (value === null || value === undefined) {
        return '';
      }

      // Handle objects (JSON stringify)
      if (typeof value === 'object') {
        return escapeCSVValue(JSON.stringify(value));
      }

      // Handle primitives
      return escapeCSVValue(String(value));
    }).join(',');
  });

  return [header, ...rows].join('\n');
}

/**
 * Escape a value for CSV format
 * @param value - Value to escape
 * @returns Escaped value
 */
function escapeCSVValue(value: string): string {
  // If value contains comma, quote, or newline, wrap in quotes and escape internal quotes
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/**
 * Create a downloadable CSV file blob
 * @param contacts - Array of contact objects
 * @param filename - Name for the downloaded file
 * @param includeEnrichmentData - Whether to include enriched fields
 * @returns Blob object for download
 */
export function createCSVBlob(
  contacts: Contact[],
  includeEnrichmentData: boolean = true
): Blob {
  const csv = contactsToCSV(contacts, includeEnrichmentData);
  return new Blob([csv], { type: 'text/csv;charset=utf-8;' });
}

/**
 * Trigger download of CSV file in browser
 * @param contacts - Array of contact objects
 * @param filename - Name for the downloaded file
 * @param includeEnrichmentData - Whether to include enriched fields
 */
export function downloadCSV(
  contacts: Contact[],
  filename: string = 'candidates.csv',
  includeEnrichmentData: boolean = true
): void {
  const blob = createCSVBlob(contacts, includeEnrichmentData);

  // Create download link and trigger click
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Clean up URL object
  URL.revokeObjectURL(url);
}

/**
 * Generate filename with timestamp
 * @param jobTitle - Job title for the search
 * @returns Filename string
 */
export function generateCSVFilename(jobTitle?: string): string {
  const timestamp = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
  const safeTitlel = jobTitle
    ? jobTitle.toLowerCase().replace(/[^a-z0-9]+/g, '_').substring(0, 30)
    : 'candidates';
  return `${safeTitlel}_${timestamp}.csv`;
}
