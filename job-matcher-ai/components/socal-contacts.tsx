'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Search,
  Loader2,
  ExternalLink,
  Mail,
  Building2,
  MapPin,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Download,
  TreePine,
  Check,
} from 'lucide-react';

interface SoCalContact {
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

type SortField = 'first_name' | 'last_name' | 'city' | 'company' | 'position' | 'donor_total_score' | 'joshua_tree_invited';

export function SoCalContacts() {
  const [contacts, setContacts] = useState<SoCalContact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortField>('city');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [stats, setStats] = useState({ total: 0, la_metro: 0, san_diego: 0, invited: 0 });
  const [updatingIds, setUpdatingIds] = useState<Set<number>>(new Set());
  const [showInvitedOnly, setShowInvitedOnly] = useState(false);

  useEffect(() => {
    fetchContacts();
  }, [sortBy, sortOrder]);

  const fetchContacts = async (searchTerm?: string) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        sortBy,
        sortOrder,
        ...(searchTerm && { search: searchTerm }),
      });

      const response = await fetch(`/api/socal-contacts?${params}`);
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setContacts(data.contacts);
      setStats({
        total: data.total,
        la_metro: data.regions.la_metro,
        san_diego: data.regions.san_diego,
        invited: data.invited_count || 0,
      });
    } catch (error) {
      console.error('Failed to fetch contacts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchContacts(search);
  };

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  const toggleInvitation = async (contactId: number, currentStatus: boolean | null) => {
    setUpdatingIds(prev => new Set(prev).add(contactId));

    try {
      const response = await fetch('/api/socal-contacts', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contactId,
          invited: !currentStatus,
        }),
      });

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Update local state
      setContacts(prev =>
        prev.map(c =>
          c.id === contactId
            ? {
                ...c,
                joshua_tree_invited: data.contact.joshua_tree_invited,
                joshua_tree_invited_at: data.contact.joshua_tree_invited_at,
              }
            : c
        )
      );

      // Update invited count
      setStats(prev => ({
        ...prev,
        invited: prev.invited + (data.contact.joshua_tree_invited ? 1 : -1),
      }));
    } catch (error) {
      console.error('Failed to update invitation:', error);
    } finally {
      setUpdatingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(contactId);
        return newSet;
      });
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortBy !== field) return <ArrowUpDown className="w-4 h-4 ml-1 opacity-50" />;
    return sortOrder === 'asc' ? (
      <ArrowUp className="w-4 h-4 ml-1" />
    ) : (
      <ArrowDown className="w-4 h-4 ml-1" />
    );
  };

  const getBestEmail = (contact: SoCalContact) => {
    return contact.work_email || contact.personal_email || contact.email;
  };

  const getTierColor = (tier: string | null) => {
    if (!tier) return 'bg-gray-100 text-gray-700';
    if (tier.includes('1')) return 'bg-green-100 text-green-800';
    if (tier.includes('2')) return 'bg-blue-100 text-blue-800';
    if (tier.includes('3')) return 'bg-yellow-100 text-yellow-800';
    if (tier.includes('4')) return 'bg-orange-100 text-orange-800';
    return 'bg-gray-100 text-gray-700';
  };

  const downloadCSV = () => {
    const headers = [
      'ID',
      'First Name',
      'Last Name',
      'Email',
      'Phone',
      'Company',
      'Position',
      'City',
      'State',
      'LinkedIn',
      'Headline',
      'Classification',
      'Donor Tier',
      'Donor Score',
      'JTree Invited',
      'JTree Invited At',
    ];

    const rows = displayedContacts.map((c) => [
      c.id,
      c.first_name || '',
      c.last_name || '',
      getBestEmail(c) || '',
      c.normalized_phone_number || '',
      c.company || '',
      c.position || '',
      c.city || '',
      c.state || '',
      c.linkedin_url || '',
      (c.headline || '').replace(/"/g, '""'),
      c.taxonomy_classification || '',
      c.donor_tier || '',
      c.donor_total_score || '',
      c.joshua_tree_invited ? 'Yes' : 'No',
      c.joshua_tree_invited_at || '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) =>
        row.map((cell) => `"${cell}"`).join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `socal_contacts_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Filter contacts based on showInvitedOnly toggle
  const displayedContacts = showInvitedOnly
    ? contacts.filter(c => c.joshua_tree_invited)
    : contacts;

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-2xl font-bold mb-2">LA & San Diego Metro Contacts</h2>
        <p className="text-muted-foreground mb-4">
          Browse and search contacts in Southern California metropolitan areas
        </p>

        <div className="flex flex-wrap gap-3 mb-4">
          <div className="bg-blue-50 px-4 py-2 rounded-lg">
            <span className="text-sm text-blue-600 font-medium">Total: {stats.total}</span>
          </div>
          <div className="bg-purple-50 px-4 py-2 rounded-lg">
            <span className="text-sm text-purple-600 font-medium">LA Metro: {stats.la_metro}</span>
          </div>
          <div className="bg-orange-50 px-4 py-2 rounded-lg">
            <span className="text-sm text-orange-600 font-medium">San Diego: {stats.san_diego}</span>
          </div>
          <button
            onClick={() => setShowInvitedOnly(!showInvitedOnly)}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
              showInvitedOnly
                ? 'bg-green-500 text-white'
                : 'bg-green-50 text-green-700 hover:bg-green-100'
            }`}
          >
            <TreePine className="w-4 h-4" />
            <span className="text-sm font-medium">
              Joshua Tree: {stats.invited}
            </span>
          </button>
        </div>

        <div className="flex gap-2">
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name, company, position, city..."
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <Button type="submit" disabled={isLoading}>
              Search
            </Button>
          </form>
          <Button variant="outline" onClick={downloadCSV} disabled={isLoading || displayedContacts.length === 0}>
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      <Card className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <ScrollArea className="h-[calc(100vh-320px)]">
            <table className="w-full">
              <thead className="bg-muted sticky top-0">
                <tr>
                  <th className="text-left p-3 w-10">
                    <button
                      onClick={() => handleSort('joshua_tree_invited')}
                      className="flex items-center font-medium hover:text-primary"
                      title="Joshua Tree Trip"
                    >
                      <TreePine className="w-4 h-4" />
                      {getSortIcon('joshua_tree_invited')}
                    </button>
                  </th>
                  <th className="text-left p-3">
                    <button
                      onClick={() => handleSort('first_name')}
                      className="flex items-center font-medium hover:text-primary"
                    >
                      Name {getSortIcon('first_name')}
                    </button>
                  </th>
                  <th className="text-left p-3">
                    <button
                      onClick={() => handleSort('company')}
                      className="flex items-center font-medium hover:text-primary"
                    >
                      Company {getSortIcon('company')}
                    </button>
                  </th>
                  <th className="text-left p-3">
                    <button
                      onClick={() => handleSort('position')}
                      className="flex items-center font-medium hover:text-primary"
                    >
                      Position {getSortIcon('position')}
                    </button>
                  </th>
                  <th className="text-left p-3">
                    <button
                      onClick={() => handleSort('city')}
                      className="flex items-center font-medium hover:text-primary"
                    >
                      Location {getSortIcon('city')}
                    </button>
                  </th>
                  <th className="text-left p-3">Contact</th>
                  <th className="text-left p-3">
                    <button
                      onClick={() => handleSort('donor_total_score')}
                      className="flex items-center font-medium hover:text-primary"
                    >
                      Tier {getSortIcon('donor_total_score')}
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {displayedContacts.map((contact) => (
                  <tr
                    key={contact.id}
                    className={`border-b hover:bg-muted/50 transition-colors ${
                      contact.joshua_tree_invited ? 'bg-green-50/50' : ''
                    }`}
                  >
                    <td className="p-3">
                      <button
                        onClick={() => toggleInvitation(contact.id, contact.joshua_tree_invited)}
                        disabled={updatingIds.has(contact.id)}
                        className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                          contact.joshua_tree_invited
                            ? 'bg-green-500 text-white hover:bg-green-600'
                            : 'bg-gray-100 text-gray-400 hover:bg-green-100 hover:text-green-600'
                        }`}
                        title={contact.joshua_tree_invited ? 'Remove from JTree trip' : 'Invite to JTree trip'}
                      >
                        {updatingIds.has(contact.id) ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : contact.joshua_tree_invited ? (
                          <Check className="w-4 h-4" />
                        ) : (
                          <TreePine className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                    <td className="p-3">
                      <div className="font-medium">
                        {contact.first_name} {contact.last_name}
                      </div>
                      {contact.headline && (
                        <div className="text-xs text-muted-foreground truncate max-w-[200px]">
                          {contact.headline}
                        </div>
                      )}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-1">
                        <Building2 className="w-3 h-3 text-muted-foreground" />
                        <span className="text-sm">{contact.company || '-'}</span>
                      </div>
                    </td>
                    <td className="p-3">
                      <span className="text-sm">{contact.position || '-'}</span>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-muted-foreground" />
                        <span className="text-sm">{contact.city || '-'}</span>
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        {getBestEmail(contact) && (
                          <a
                            href={`mailto:${getBestEmail(contact)}`}
                            className="text-blue-600 hover:text-blue-800"
                            title={getBestEmail(contact) || ''}
                          >
                            <Mail className="w-4 h-4" />
                          </a>
                        )}
                        {contact.linkedin_url && (
                          <a
                            href={contact.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800"
                            title="LinkedIn Profile"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      {contact.donor_tier && (
                        <span
                          className={`text-xs px-2 py-1 rounded-full ${getTierColor(
                            contact.donor_tier
                          )}`}
                        >
                          {contact.donor_tier.replace('Tier ', 'T').split(':')[0]}
                        </span>
                      )}
                      {contact.donor_total_score && (
                        <span className="text-xs text-muted-foreground ml-1">
                          ({contact.donor_total_score})
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {displayedContacts.length === 0 && (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-muted-foreground">
                      {showInvitedOnly
                        ? 'No contacts have been invited to the Joshua Tree trip yet.'
                        : 'No contacts found matching your search criteria.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </ScrollArea>
        )}
      </Card>
    </div>
  );
}
