const { useState, useEffect, useMemo } = React;

// Initialize Supabase client
const supabaseUrl = 'https://ypqsrejrsocebnldicke.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlwcXNyZWpyc29jZWJubGRpY2tlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYzMTk1NDQsImV4cCI6MjA1MTg5NTU0NH0.MdnHIyb_0GwQpTJjaBUx8g4kGizPRuAdPNFQhhqRQP8'; // Supabase anon (public) key - safe for client-side
const supabase = window.supabase.createClient(supabaseUrl, supabaseKey);

// Simple auth hook
function useAuth() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check active session
        supabase.auth.getSession().then(({ data: { session } }) => {
            setUser(session?.user ?? null);
            setLoading(false);
        });

        // Listen for auth changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null);
        });

        return () => subscription.unsubscribe();
    }, []);

    return { user, loading };
}

// Login Component
function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        const { error } = await supabase.auth.signInWithPassword({ email, password });

        if (error) {
            setError(error.message);
        }
        setLoading(false);
    };

    return (
        <div className="login-container">
            <div className="login-box">
                <h1 className="login-title">Donor Prospects</h1>
                <p className="login-subtitle">Outdoorithm Collective</p>

                <form onSubmit={handleLogin} className="login-form">
                    {error && <div className="login-error">{error}</div>}

                    <div className="form-field">
                        <label>Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            autoComplete="email"
                        />
                    </div>

                    <div className="form-field">
                        <label>Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            autoComplete="current-password"
                        />
                    </div>

                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>
            </div>
        </div>
    );
}

// Main App Component
function App() {
    const { user, loading: authLoading } = useAuth();

    // Show login if not authenticated (before any conditional hooks)
    if (authLoading) {
        return <div className="loading">Loading...</div>;
    }

    if (!user) {
        return <Login />;
    }

    return <AuthenticatedApp />;
}

// Authenticated App Component (all hooks here run consistently)
function AuthenticatedApp() {
    const [prospects, setProspects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedProspect, setSelectedProspect] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortBy, setSortBy] = useState('warmth');

    // Filter states
    const [filters, setFilters] = useState({
        boardMember: false,
        knownDonor: false,
        outdoorAffinity: false,
        equityFocus: false,
        familyFocus: false,
        warmthHot: false,
        warmthWarm: false,
        warmthCool: false,
        warmthCold: false,
        // Outreach filters
        hasBeenContacted: false,
        neverContacted: false,
        contacted30Days: false,
        contacted90Days: false
    });

    // Fetch prospects from Supabase
    useEffect(() => {
        fetchProspects();
    }, []);

    const fetchProspects = async () => {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('contacts')
                .select('*')
                .not('cultivation_notes', 'is', null)
                .order('personal_connection_strength', { ascending: false });

            if (error) throw error;
            setProspects(data || []);
        } catch (error) {
            console.error('Error fetching prospects:', error);
        } finally {
            setLoading(false);
        }
    };

    // Filter and sort prospects
    const filteredProspects = useMemo(() => {
        let filtered = [...prospects];

        // Apply search filter
        if (searchTerm) {
            const search = searchTerm.toLowerCase();
            filtered = filtered.filter(p =>
                `${p.first_name} ${p.last_name}`.toLowerCase().includes(search) ||
                (p.enrich_current_company || '').toLowerCase().includes(search) ||
                (p.enrich_current_title || '').toLowerCase().includes(search) ||
                (p.email || '').toLowerCase().includes(search) ||
                (p.work_email || '').toLowerCase().includes(search) ||
                (p.personal_email || '').toLowerCase().includes(search)
            );
        }

        // Apply boolean filters
        if (filters.boardMember) {
            filtered = filtered.filter(p => p.nonprofit_board_member === true);
        }
        if (filters.knownDonor) {
            filtered = filtered.filter(p => p.known_donor === true);
        }
        if (filters.outdoorAffinity) {
            filtered = filtered.filter(p => p.outdoor_environmental_affinity === true);
        }
        if (filters.equityFocus) {
            filtered = filtered.filter(p => p.equity_access_focus === true);
        }
        if (filters.familyFocus) {
            filtered = filtered.filter(p => p.family_youth_focus === true);
        }

        // Apply warmth filters
        const warmthFilters = [];
        if (filters.warmthHot) warmthFilters.push('Hot');
        if (filters.warmthWarm) warmthFilters.push('Warm');
        if (filters.warmthCool) warmthFilters.push('Cool');
        if (filters.warmthCold) warmthFilters.push('Cold');

        if (warmthFilters.length > 0) {
            filtered = filtered.filter(p => warmthFilters.includes(p.warmth_level));
        }

        // Apply outreach filters
        const now = new Date();
        if (filters.hasBeenContacted) {
            filtered = filtered.filter(p => p.last_contact_date !== null);
        }
        if (filters.neverContacted) {
            filtered = filtered.filter(p => p.last_contact_date === null);
        }
        if (filters.contacted30Days) {
            filtered = filtered.filter(p => {
                if (!p.last_contact_date) return false;
                const daysSince = (now - new Date(p.last_contact_date)) / (1000 * 60 * 60 * 24);
                return daysSince <= 30;
            });
        }
        if (filters.contacted90Days) {
            filtered = filtered.filter(p => {
                if (!p.last_contact_date) return false;
                const daysSince = (now - new Date(p.last_contact_date)) / (1000 * 60 * 60 * 24);
                return daysSince <= 90;
            });
        }

        // Apply sorting
        filtered.sort((a, b) => {
            switch (sortBy) {
                case 'warmth':
                    return (b.personal_connection_strength || 0) - (a.personal_connection_strength || 0);
                case 'name':
                    return `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
                case 'capacity':
                    return (b.donor_capacity_score || 0) - (a.donor_capacity_score || 0);
                case 'affinity':
                    return (b.donor_affinity_score || 0) - (a.donor_affinity_score || 0);
                default:
                    return 0;
            }
        });

        return filtered;
    }, [prospects, searchTerm, filters, sortBy]);

    // Toggle filter
    const toggleFilter = (filterKey) => {
        setFilters(prev => ({
            ...prev,
            [filterKey]: !prev[filterKey]
        }));
    };

    // Clear all filters
    const clearFilters = () => {
        setFilters({
            boardMember: false,
            knownDonor: false,
            outdoorAffinity: false,
            equityFocus: false,
            familyFocus: false,
            warmthHot: false,
            warmthWarm: false,
            warmthCool: false,
            warmthCold: false,
            hasBeenContacted: false,
            neverContacted: false,
            contacted30Days: false,
            contacted90Days: false
        });
        setSearchTerm('');
    };

    // Get active filter count
    const activeFilterCount = Object.values(filters).filter(Boolean).length + (searchTerm ? 1 : 0);

    // Count prospects by category
    const stats = useMemo(() => {
        return {
            total: prospects.length,
            boardMembers: prospects.filter(p => p.nonprofit_board_member).length,
            donors: prospects.filter(p => p.known_donor).length,
            highAffinity: prospects.filter(p => p.outdoor_environmental_affinity || p.equity_access_focus).length
        };
    }, [prospects]);

    return (
        <>
            <Header stats={stats} />
            <div className="app-container">
                <FiltersSidebar
                    filters={filters}
                    toggleFilter={toggleFilter}
                    clearFilters={clearFilters}
                    searchTerm={searchTerm}
                    setSearchTerm={setSearchTerm}
                    activeFilterCount={activeFilterCount}
                    stats={stats}
                />
                <ProspectsMain
                    prospects={filteredProspects}
                    loading={loading}
                    sortBy={sortBy}
                    setSortBy={setSortBy}
                    onSelectProspect={setSelectedProspect}
                />
            </div>
            {selectedProspect && (
                <ProspectModal
                    prospect={selectedProspect}
                    onClose={() => setSelectedProspect(null)}
                    onUpdate={fetchProspects}
                />
            )}
        </>
    );
}

// Header Component
function Header({ stats }) {
    const handleLogout = async () => {
        await supabase.auth.signOut();
    };

    return (
        <header className="app-header">
            <div className="header-content">
                <div>
                    <h1 className="app-title">Donor Prospects</h1>
                    <p className="app-subtitle">Outdoorithm Collective</p>
                </div>
                <div className="header-stats">
                    <div className="stat">
                        <div className="stat-value">{stats.total}</div>
                        <div className="stat-label">Total Prospects</div>
                    </div>
                    <div className="stat">
                        <div className="stat-value">{stats.boardMembers}</div>
                        <div className="stat-label">Board Members</div>
                    </div>
                    <div className="stat">
                        <div className="stat-value">{stats.donors}</div>
                        <div className="stat-label">Known Donors</div>
                    </div>
                    <div className="stat">
                        <div className="stat-value">{stats.highAffinity}</div>
                        <div className="stat-label">High Affinity</div>
                    </div>
                </div>
                <button className="btn btn-secondary btn-small" onClick={handleLogout}>
                    Sign Out
                </button>
            </div>
        </header>
    );
}

// Filters Sidebar Component
function FiltersSidebar({ filters, toggleFilter, clearFilters, searchTerm, setSearchTerm, activeFilterCount, stats }) {
    return (
        <aside className="filters-sidebar">
            <div className="filters-header">
                <h2 className="filters-title">Filters</h2>
                {activeFilterCount > 0 && (
                    <button className="clear-filters" onClick={clearFilters}>
                        Clear all ({activeFilterCount})
                    </button>
                )}
            </div>

            {/* Search */}
            <div className="filter-group">
                <div className="filter-group-title">Search</div>
                <input
                    type="text"
                    className="search-input"
                    placeholder="Search by name, company, title, email..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>

            {/* Philanthropic Activity */}
            <div className="filter-group">
                <div className="filter-group-title">Philanthropic Activity</div>
                <div className="filter-options">
                    <FilterCheckbox
                        label="Board Member"
                        checked={filters.boardMember}
                        onChange={() => toggleFilter('boardMember')}
                        count={stats.boardMembers}
                    />
                    <FilterCheckbox
                        label="Known Donor"
                        checked={filters.knownDonor}
                        onChange={() => toggleFilter('knownDonor')}
                        count={stats.donors}
                    />
                </div>
            </div>

            {/* Mission Affinity */}
            <div className="filter-group">
                <div className="filter-group-title">Mission Affinity</div>
                <div className="filter-options">
                    <FilterCheckbox
                        label="Outdoor/Environmental"
                        checked={filters.outdoorAffinity}
                        onChange={() => toggleFilter('outdoorAffinity')}
                    />
                    <FilterCheckbox
                        label="Equity/DEI Focus"
                        checked={filters.equityFocus}
                        onChange={() => toggleFilter('equityFocus')}
                    />
                    <FilterCheckbox
                        label="Family/Youth Focus"
                        checked={filters.familyFocus}
                        onChange={() => toggleFilter('familyFocus')}
                    />
                </div>
            </div>

            {/* Warmth Level */}
            <div className="filter-group">
                <div className="filter-group-title">Warmth Level</div>
                <div className="filter-options">
                    <FilterCheckbox
                        label="Hot"
                        checked={filters.warmthHot}
                        onChange={() => toggleFilter('warmthHot')}
                    />
                    <FilterCheckbox
                        label="Warm"
                        checked={filters.warmthWarm}
                        onChange={() => toggleFilter('warmthWarm')}
                    />
                    <FilterCheckbox
                        label="Cool"
                        checked={filters.warmthCool}
                        onChange={() => toggleFilter('warmthCool')}
                    />
                    <FilterCheckbox
                        label="Cold"
                        checked={filters.warmthCold}
                        onChange={() => toggleFilter('warmthCold')}
                    />
                </div>
            </div>

            {/* Outreach Status */}
            <div className="filter-group">
                <div className="filter-group-title">Outreach Status</div>
                <div className="filter-options">
                    <FilterCheckbox
                        label="Has Been Contacted"
                        checked={filters.hasBeenContacted}
                        onChange={() => toggleFilter('hasBeenContacted')}
                    />
                    <FilterCheckbox
                        label="Never Contacted"
                        checked={filters.neverContacted}
                        onChange={() => toggleFilter('neverContacted')}
                    />
                    <FilterCheckbox
                        label="Contacted (Last 30 Days)"
                        checked={filters.contacted30Days}
                        onChange={() => toggleFilter('contacted30Days')}
                    />
                    <FilterCheckbox
                        label="Contacted (Last 90 Days)"
                        checked={filters.contacted90Days}
                        onChange={() => toggleFilter('contacted90Days')}
                    />
                </div>
            </div>
        </aside>
    );
}

// Filter Checkbox Component
function FilterCheckbox({ label, checked, onChange, count }) {
    return (
        <div className="filter-checkbox">
            <input type="checkbox" checked={checked} onChange={onChange} id={label} />
            <label htmlFor={label}>{label}</label>
            {count !== undefined && <span className="filter-count">{count}</span>}
        </div>
    );
}

// Prospects Main Component
function ProspectsMain({ prospects, loading, sortBy, setSortBy, onSelectProspect }) {
    if (loading) {
        return (
            <main className="prospects-main">
                <div className="loading">Loading prospects...</div>
            </main>
        );
    }

    return (
        <main className="prospects-main">
            <div className="prospects-header">
                <div className="results-count">
                    {prospects.length} {prospects.length === 1 ? 'prospect' : 'prospects'}
                </div>
                <select
                    className="sort-select"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                >
                    <option value="warmth">Sort by Warmth</option>
                    <option value="name">Sort by Name</option>
                    <option value="capacity">Sort by Capacity</option>
                    <option value="affinity">Sort by Affinity</option>
                </select>
            </div>

            {prospects.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-state-icon">🔍</div>
                    <h3 className="empty-state-title">No prospects found</h3>
                    <p className="empty-state-description">
                        Try adjusting your filters or search criteria
                    </p>
                </div>
            ) : (
                <div className="prospects-grid">
                    {prospects.map(prospect => (
                        <ProspectCard
                            key={prospect.id}
                            prospect={prospect}
                            onClick={() => onSelectProspect(prospect)}
                        />
                    ))}
                </div>
            )}
        </main>
    );
}

// Prospect Card Component
function ProspectCard({ prospect, onClick }) {
    const name = `${prospect.first_name || ''} ${prospect.last_name || ''}`.trim();
    const title = prospect.enrich_current_title || prospect.position || '';
    const company = prospect.enrich_current_company || prospect.company || '';
    const warmth = prospect.warmth_level || 'Cold';
    const connectionStrength = prospect.personal_connection_strength || 0;

    // Get cultivation notes preview (first 200 chars of KEY FINDINGS)
    const cultivationPreview = prospect.cultivation_notes
        ? prospect.cultivation_notes.split('RECOMMENDED APPROACH:')[0]
            .replace('KEY FINDINGS:', '')
            .trim()
            .substring(0, 200) + '...'
        : '';

    return (
        <article className="prospect-card" onClick={onClick}>
            <div className="card-header">
                <div>
                    <h3 className="prospect-name">{name}</h3>
                    {(title || company) && (
                        <p className="prospect-title">
                            {title}{title && company ? ' at ' : ''}{company}
                        </p>
                    )}
                </div>
                <div className={`warmth-badge warmth-${warmth.toLowerCase()}`}>
                    {warmth}
                </div>
            </div>

            <div className="card-indicators">
                {prospect.nonprofit_board_member && (
                    <span className="indicator">
                        <span className="indicator-icon">🏛️</span>
                        Board Member
                    </span>
                )}
                {prospect.known_donor && (
                    <span className="indicator">
                        <span className="indicator-icon">💝</span>
                        Known Donor
                    </span>
                )}
                {prospect.last_contact_date && (
                    <span className="indicator indicator-contact">
                        <span className="indicator-icon">📞</span>
                        Last contact: {new Date(prospect.last_contact_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                )}
            </div>

            {(prospect.outdoor_environmental_affinity || prospect.equity_access_focus || prospect.family_youth_focus) && (
                <div className="card-affinity">
                    {prospect.outdoor_environmental_affinity && (
                        <span className="affinity-tag">🌲 Outdoor</span>
                    )}
                    {prospect.equity_access_focus && (
                        <span className="affinity-tag">⚖️ Equity</span>
                    )}
                    {prospect.family_youth_focus && (
                        <span className="affinity-tag">👨‍👩‍👧 Family</span>
                    )}
                </div>
            )}

            {/* AI Scores Section */}
            {(prospect.donor_capacity_score || prospect.donor_propensity_score || prospect.donor_affinity_score) && (
                <div className="card-scores">
                    {prospect.donor_capacity_score !== null && (
                        <div className="score-item">
                            <div className="score-label">Capacity</div>
                            <div className="score-bar">
                                <div className="score-fill" style={{width: `${prospect.donor_capacity_score}%`}}></div>
                            </div>
                            <div className="score-value">{prospect.donor_capacity_score}/100</div>
                        </div>
                    )}
                    {prospect.donor_propensity_score !== null && (
                        <div className="score-item">
                            <div className="score-label">Propensity</div>
                            <div className="score-bar">
                                <div className="score-fill" style={{width: `${prospect.donor_propensity_score}%`}}></div>
                            </div>
                            <div className="score-value">{prospect.donor_propensity_score}/100</div>
                        </div>
                    )}
                    {prospect.donor_affinity_score !== null && (
                        <div className="score-item">
                            <div className="score-label">Affinity</div>
                            <div className="score-bar">
                                <div className="score-fill" style={{width: `${prospect.donor_affinity_score}%`}}></div>
                            </div>
                            <div className="score-value">{prospect.donor_affinity_score}/100</div>
                        </div>
                    )}
                </div>
            )}

            {cultivationPreview && (
                <div className="card-cultivation">{cultivationPreview}</div>
            )}

            <div className="card-footer">
                <div className="connection-strength">
                    {prospect.donor_tier && <span className="tier-badge">{prospect.donor_tier.replace('Tier ', 'T')}</span>}
                    {prospect.estimated_capacity && <span className="capacity-badge">{prospect.estimated_capacity}</span>}
                    Connection: {connectionStrength}/10
                </div>
                <span className="view-details">View details →</span>
            </div>
        </article>
    );
}

// Prospect Modal Component
function ProspectModal({ prospect, onClose, onUpdate }) {
    const [editedData, setEditedData] = useState({
        warmth_level: prospect.warmth_level || 'Cold',
        personal_connection_strength: prospect.personal_connection_strength || 0,
        relationship_notes: prospect.relationship_notes || '',
        cultivation_stage: prospect.cultivation_stage || 'Not Started',
        next_touchpoint_date: prospect.next_touchpoint_date || '',
        next_touchpoint_type: prospect.next_touchpoint_type || '',
        // Contact information fields
        email: prospect.email || '',
        work_email: prospect.work_email || '',
        personal_email: prospect.personal_email || '',
        email_verified: prospect.email_verified || false
    });
    const [saving, setSaving] = useState(false);

    // Outreach logging state
    const [showOutreachForm, setShowOutreachForm] = useState(false);
    const [outreachForm, setOutreachForm] = useState({
        date: new Date().toISOString().split('T')[0],
        type: 'email',
        subject: '',
        notes: '',
        outcome: 'sent'
    });

    const handleSave = async () => {
        try {
            setSaving(true);
            const { error } = await supabase
                .from('contacts')
                .update(editedData)
                .eq('id', prospect.id);

            if (error) throw error;

            alert('Prospect updated successfully!');
            onUpdate();
            onClose();
        } catch (error) {
            console.error('Error updating prospect:', error);
            alert('Error updating prospect. Please try again.');
        } finally {
            setSaving(false);
        }
    };

    const handleLogOutreach = async () => {
        try {
            setSaving(true);

            // Use secure RPC function for atomic, validated outreach logging
            const { data, error } = await supabase.rpc('log_outreach', {
                p_contact_id: prospect.id,
                p_date: outreachForm.date,
                p_type: outreachForm.type,
                p_subject: outreachForm.subject,
                p_notes: outreachForm.notes,
                p_outcome: outreachForm.outcome
            });

            if (error) throw error;

            // Fetch updated prospect data to refresh modal
            const { data: updatedProspect, error: fetchError } = await supabase
                .from('contacts')
                .select('*')
                .eq('id', prospect.id)
                .single();

            if (fetchError) throw fetchError;

            // Update the modal with fresh data
            Object.assign(prospect, updatedProspect);

            // Reset form
            setOutreachForm({
                date: new Date().toISOString().split('T')[0],
                type: 'email',
                subject: '',
                notes: '',
                outcome: 'sent'
            });
            setShowOutreachForm(false);

            alert('Outreach logged successfully!');
            onUpdate(); // Refresh the main list
        } catch (error) {
            console.error('Error logging outreach:', error);
            alert('Error logging outreach: ' + error.message);
        } finally {
            setSaving(false);
        }
    };

    const name = `${prospect.first_name || ''} ${prospect.last_name || ''}`.trim();
    const title = prospect.enrich_current_title || prospect.position || 'Unknown';
    const company = prospect.enrich_current_company || prospect.company || 'Unknown';

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <button className="modal-close" onClick={onClose}>×</button>
                    <h2 className="modal-title">{name}</h2>
                    <p className="modal-subtitle">{title} at {company}</p>
                </div>

                <div className="modal-body">
                    {/* Overview */}
                    <div className="detail-section">
                        <h3 className="section-title">Overview</h3>
                        <div className="detail-grid">
                            <div className="detail-item">
                                <div className="detail-label">Location</div>
                                <div className="detail-value">{prospect.location_name || 'Unknown'}</div>
                            </div>
                            <div className="detail-item">
                                <div className="detail-label">Connection Type</div>
                                <div className="detail-value">{prospect.connection_type || 'Unknown'}</div>
                            </div>
                        </div>
                    </div>

                    {/* Contact Information (Editable) */}
                    <div className="detail-section">
                        <h3 className="section-title">Contact Information (Editable)</h3>

                        <div className="editable-field">
                            <label>Primary Email</label>
                            <div className="email-input-wrapper">
                                <input
                                    type="email"
                                    placeholder="primary@email.com"
                                    value={editedData.email}
                                    onChange={(e) => setEditedData({ ...editedData, email: e.target.value })}
                                />
                                <div className="email-verified-toggle">
                                    <input
                                        type="checkbox"
                                        id="email-verified"
                                        checked={editedData.email_verified}
                                        onChange={(e) => setEditedData({ ...editedData, email_verified: e.target.checked })}
                                    />
                                    <label htmlFor="email-verified">Verified</label>
                                </div>
                            </div>
                        </div>

                        <div className="editable-field">
                            <label>Work Email</label>
                            <input
                                type="email"
                                placeholder="work@company.com"
                                value={editedData.work_email}
                                onChange={(e) => setEditedData({ ...editedData, work_email: e.target.value })}
                            />
                        </div>

                        <div className="editable-field">
                            <label>Personal Email</label>
                            <input
                                type="email"
                                placeholder="personal@email.com"
                                value={editedData.personal_email}
                                onChange={(e) => setEditedData({ ...editedData, personal_email: e.target.value })}
                            />
                        </div>
                    </div>

                    {/* AI Scores Section */}
                    {(prospect.donor_capacity_score !== null || prospect.donor_propensity_score !== null ||
                      prospect.donor_affinity_score !== null || prospect.donor_warmth_score !== null) && (
                        <div className="detail-section">
                            <h3 className="section-title">AI Prospect Scores</h3>
                            <div className="scores-grid">
                                {prospect.donor_capacity_score !== null && (
                                    <div className="score-detail">
                                        <div className="score-detail-header">
                                            <span className="score-detail-label">Capacity Score</span>
                                            <span className="score-detail-value">{prospect.donor_capacity_score}/100</span>
                                        </div>
                                        <div className="score-detail-bar">
                                            <div className="score-detail-fill score-capacity" style={{width: `${prospect.donor_capacity_score}%`}}></div>
                                        </div>
                                        <div className="score-detail-desc">Financial ability to give (title, company, experience)</div>
                                    </div>
                                )}
                                {prospect.donor_propensity_score !== null && (
                                    <div className="score-detail">
                                        <div className="score-detail-header">
                                            <span className="score-detail-label">Propensity Score</span>
                                            <span className="score-detail-value">{prospect.donor_propensity_score}/100</span>
                                        </div>
                                        <div className="score-detail-bar">
                                            <div className="score-detail-fill score-propensity" style={{width: `${prospect.donor_propensity_score}%`}}></div>
                                        </div>
                                        <div className="score-detail-desc">Likelihood to give (board service, past donations)</div>
                                    </div>
                                )}
                                {prospect.donor_affinity_score !== null && (
                                    <div className="score-detail">
                                        <div className="score-detail-header">
                                            <span className="score-detail-label">Affinity Score</span>
                                            <span className="score-detail-value">{prospect.donor_affinity_score}/100</span>
                                        </div>
                                        <div className="score-detail-bar">
                                            <div className="score-detail-fill score-affinity" style={{width: `${prospect.donor_affinity_score}%`}}></div>
                                        </div>
                                        <div className="score-detail-desc">Mission alignment (outdoor, equity, family focus)</div>
                                    </div>
                                )}
                                {prospect.donor_warmth_score !== null && (
                                    <div className="score-detail">
                                        <div className="score-detail-header">
                                            <span className="score-detail-label">Warmth Score</span>
                                            <span className="score-detail-value">{prospect.donor_warmth_score}/100</span>
                                        </div>
                                        <div className="score-detail-bar">
                                            <div className="score-detail-fill score-warmth" style={{width: `${prospect.donor_warmth_score}%`}}></div>
                                        </div>
                                        <div className="score-detail-desc">Relationship strength (shared institutions, connections)</div>
                                    </div>
                                )}
                                {prospect.donor_total_score !== null && (
                                    <div className="score-detail score-total-wrapper">
                                        <div className="score-detail-header">
                                            <span className="score-detail-label">Total Score</span>
                                            <span className="score-detail-value total-score">{prospect.donor_total_score}/100</span>
                                        </div>
                                        <div className="score-detail-bar">
                                            <div className="score-detail-fill score-total" style={{width: `${prospect.donor_total_score}%`}}></div>
                                        </div>
                                        <div className="score-detail-desc">Weighted: Capacity(30%) + Propensity(40%) + Affinity(20%) + Warmth(10%)</div>
                                    </div>
                                )}
                            </div>
                            {(prospect.donor_tier || prospect.estimated_capacity) && (
                                <div className="score-badges">
                                    {prospect.donor_tier && <div className="tier-badge-large">{prospect.donor_tier}</div>}
                                    {prospect.estimated_capacity && <div className="capacity-badge-large">Est. Capacity: {prospect.estimated_capacity}</div>}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Outreach History */}
                    <div className="detail-section">
                        <div className="section-header-with-action">
                            <h3 className="section-title">Outreach History</h3>
                            <button
                                className="btn btn-small btn-primary"
                                onClick={() => setShowOutreachForm(!showOutreachForm)}
                            >
                                {showOutreachForm ? 'Cancel' : '+ Log Outreach'}
                            </button>
                        </div>

                        {/* Outreach Logging Form */}
                        {showOutreachForm && (
                            <div className="outreach-form">
                                <div className="form-row">
                                    <div className="form-field">
                                        <label>Date</label>
                                        <input
                                            type="date"
                                            value={outreachForm.date}
                                            onChange={(e) => setOutreachForm({...outreachForm, date: e.target.value})}
                                        />
                                    </div>
                                    <div className="form-field">
                                        <label>Type</label>
                                        <select
                                            value={outreachForm.type}
                                            onChange={(e) => setOutreachForm({...outreachForm, type: e.target.value})}
                                        >
                                            <option value="email">Email</option>
                                            <option value="call">Phone Call</option>
                                            <option value="meeting">In-Person Meeting</option>
                                            <option value="video">Video Call</option>
                                            <option value="text">Text Message</option>
                                            <option value="linkedin">LinkedIn Message</option>
                                        </select>
                                    </div>
                                    <div className="form-field">
                                        <label>Outcome</label>
                                        <select
                                            value={outreachForm.outcome}
                                            onChange={(e) => setOutreachForm({...outreachForm, outcome: e.target.value})}
                                        >
                                            <option value="sent">Sent</option>
                                            <option value="positive">Positive Response</option>
                                            <option value="neutral">Neutral Response</option>
                                            <option value="no_response">No Response</option>
                                            <option value="declined">Declined</option>
                                            <option value="scheduled">Meeting Scheduled</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="form-field">
                                    <label>Subject/Title</label>
                                    <input
                                        type="text"
                                        placeholder="e.g., Introduction to Outdoorithm"
                                        value={outreachForm.subject}
                                        onChange={(e) => setOutreachForm({...outreachForm, subject: e.target.value})}
                                    />
                                </div>
                                <div className="form-field">
                                    <label>Notes</label>
                                    <textarea
                                        placeholder="Add details about this interaction..."
                                        value={outreachForm.notes}
                                        onChange={(e) => setOutreachForm({...outreachForm, notes: e.target.value})}
                                        rows="3"
                                    />
                                </div>
                                <button
                                    className="btn btn-primary"
                                    onClick={handleLogOutreach}
                                    disabled={saving}
                                >
                                    {saving ? 'Logging...' : 'Log Outreach'}
                                </button>
                            </div>
                        )}

                        {/* Outreach Timeline */}
                        {prospect.outreach_history && prospect.outreach_history.length > 0 ? (
                            <div className="outreach-timeline">
                                {[...prospect.outreach_history]
                                    .sort((a, b) => new Date(b.date) - new Date(a.date))
                                    .map((entry, index) => (
                                        <div key={index} className="timeline-entry">
                                            <div className="timeline-marker"></div>
                                            <div className="timeline-content">
                                                <div className="timeline-header">
                                                    <span className="timeline-type">
                                                        {entry.type === 'email' && '📧'}
                                                        {entry.type === 'call' && '📞'}
                                                        {entry.type === 'meeting' && '🤝'}
                                                        {entry.type === 'video' && '📹'}
                                                        {entry.type === 'text' && '💬'}
                                                        {entry.type === 'linkedin' && '💼'}
                                                        {' '}{entry.type.charAt(0).toUpperCase() + entry.type.slice(1)}
                                                    </span>
                                                    <span className="timeline-date">
                                                        {new Date(entry.date).toLocaleDateString('en-US', {
                                                            month: 'short',
                                                            day: 'numeric',
                                                            year: 'numeric'
                                                        })}
                                                    </span>
                                                </div>
                                                {entry.subject && (
                                                    <div className="timeline-subject">{entry.subject}</div>
                                                )}
                                                {entry.notes && (
                                                    <div className="timeline-notes">{entry.notes}</div>
                                                )}
                                                {entry.outcome && (
                                                    <span className={`outcome-badge outcome-${entry.outcome}`}>
                                                        {entry.outcome.replace('_', ' ')}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                            </div>
                        ) : (
                            <div className="empty-outreach">
                                <p>No outreach logged yet. Click "+ Log Outreach" to record your first interaction.</p>
                            </div>
                        )}
                    </div>

                    {/* Philanthropic Activity */}
                    <div className="detail-section">
                        <h3 className="section-title">Philanthropic Activity</h3>
                        <div className="detail-grid">
                            <div className="detail-item">
                                <div className="detail-label">Board Member</div>
                                <div className="detail-value">{prospect.nonprofit_board_member ? 'Yes' : 'No'}</div>
                            </div>
                            <div className="detail-item">
                                <div className="detail-label">Known Donor</div>
                                <div className="detail-value">{prospect.known_donor ? 'Yes' : 'No'}</div>
                            </div>
                        </div>
                        {prospect.board_service_details && prospect.board_service_details.length > 0 && (
                            <div style={{ marginTop: '1rem' }}>
                                <div className="detail-label">Board Positions</div>
                                <ul className="evidence-list">
                                    {prospect.board_service_details.map((board, i) => (
                                        <li key={i}>{board}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>

                    {/* Mission Affinity */}
                    <div className="detail-section">
                        <h3 className="section-title">Mission Affinity</h3>
                        {prospect.outdoor_environmental_affinity && prospect.outdoor_affinity_evidence && (
                            <div style={{ marginBottom: '1rem' }}>
                                <div className="detail-label">Outdoor/Environmental Evidence</div>
                                <ul className="evidence-list">
                                    {prospect.outdoor_affinity_evidence.map((ev, i) => (
                                        <li key={i}>{ev}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {prospect.equity_access_focus && prospect.equity_focus_evidence && (
                            <div style={{ marginBottom: '1rem' }}>
                                <div className="detail-label">Equity/DEI Evidence</div>
                                <ul className="evidence-list">
                                    {prospect.equity_focus_evidence.map((ev, i) => (
                                        <li key={i}>{ev}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>

                    {/* Cultivation Notes */}
                    {prospect.cultivation_notes && (
                        <div className="detail-section">
                            <h3 className="section-title">AI Research Summary</h3>
                            <div className="cultivation-notes-full">{prospect.cultivation_notes}</div>
                        </div>
                    )}

                    {/* Editable Fields */}
                    <div className="detail-section">
                        <h3 className="section-title">Cultivation Tracking (Editable)</h3>

                        <div className="editable-field">
                            <label>Warmth Level</label>
                            <select
                                value={editedData.warmth_level}
                                onChange={(e) => setEditedData({ ...editedData, warmth_level: e.target.value })}
                            >
                                <option value="Hot">Hot</option>
                                <option value="Warm">Warm</option>
                                <option value="Cool">Cool</option>
                                <option value="Cold">Cold</option>
                            </select>
                        </div>

                        <div className="editable-field">
                            <label>Connection Strength (0-10)</label>
                            <input
                                type="number"
                                min="0"
                                max="10"
                                value={editedData.personal_connection_strength}
                                onChange={(e) => setEditedData({
                                    ...editedData,
                                    personal_connection_strength: parseInt(e.target.value) || 0
                                })}
                            />
                        </div>

                        <div className="editable-field">
                            <label>Cultivation Stage</label>
                            <select
                                value={editedData.cultivation_stage}
                                onChange={(e) => setEditedData({ ...editedData, cultivation_stage: e.target.value })}
                            >
                                <option value="Not Started">Not Started</option>
                                <option value="Initial Outreach">Initial Outreach</option>
                                <option value="First Meeting">First Meeting</option>
                                <option value="Cultivating">Cultivating</option>
                                <option value="Ask Prepared">Ask Prepared</option>
                                <option value="Ask Made">Ask Made</option>
                                <option value="Closed Won">Closed Won</option>
                                <option value="Closed Lost">Closed Lost</option>
                                <option value="On Hold">On Hold</option>
                            </select>
                        </div>

                        <div className="editable-field">
                            <label>Next Touchpoint Date</label>
                            <input
                                type="date"
                                value={editedData.next_touchpoint_date}
                                onChange={(e) => setEditedData({ ...editedData, next_touchpoint_date: e.target.value })}
                            />
                        </div>

                        <div className="editable-field">
                            <label>Next Touchpoint Type</label>
                            <input
                                type="text"
                                placeholder="e.g., Email, Call, Coffee meeting"
                                value={editedData.next_touchpoint_type}
                                onChange={(e) => setEditedData({ ...editedData, next_touchpoint_type: e.target.value })}
                            />
                        </div>

                        <div className="editable-field">
                            <label>Relationship Notes</label>
                            <textarea
                                placeholder="Add your personal notes about this relationship..."
                                value={editedData.relationship_notes}
                                onChange={(e) => setEditedData({ ...editedData, relationship_notes: e.target.value })}
                            />
                        </div>
                    </div>
                </div>

                <div className="modal-footer">
                    <button className="btn btn-secondary" onClick={onClose}>
                        Cancel
                    </button>
                    <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>
        </div>
    );
}

// Render the app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
