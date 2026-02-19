'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ProspectList } from '@/lib/types';
import {
  BookmarkPlus,
  FolderOpen,
  Plus,
  ChevronDown,
  Loader2,
  Check,
} from 'lucide-react';

interface ListManagerProps {
  selectedIds: Set<number>;
  onLoadList: (list: ProspectList) => void;
}

export function ListManager({ selectedIds, onLoadList }: ListManagerProps) {
  const [lists, setLists] = useState<ProspectList[]>([]);
  const [saving, setSaving] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newListName, setNewListName] = useState('');
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const fetchLists = useCallback(async () => {
    try {
      const res = await fetch('/api/network-intel/prospect-lists');
      if (!res.ok) return;
      const data = await res.json();
      setLists(data.lists || []);
    } catch {
      // Silently fail — lists will show empty
    }
  }, []);

  useEffect(() => {
    fetchLists();
  }, [fetchLists]);

  const handleCreateList = useCallback(
    async (name: string) => {
      if (!name.trim()) return;
      setSaving(true);
      try {
        const res = await fetch('/api/network-intel/prospect-lists', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: name.trim(),
            contact_ids: Array.from(selectedIds),
          }),
        });
        if (!res.ok) throw new Error('Failed to create list');
        const created = await res.json();
        setLists((prev) => [created, ...prev]);
        setNewListName('');
        setShowCreate(false);
        setSaveSuccess(created.name);
        setTimeout(() => setSaveSuccess(null), 2000);
      } catch (err) {
        console.error('Failed to create list:', err);
      } finally {
        setSaving(false);
      }
    },
    [selectedIds]
  );

  const handleAddToExisting = useCallback(
    async (listId: string, listName: string) => {
      if (selectedIds.size === 0) return;
      setSaving(true);
      try {
        const res = await fetch(`/api/network-intel/prospect-lists/${listId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            add_contacts: Array.from(selectedIds),
          }),
        });
        if (!res.ok) throw new Error('Failed to add contacts');
        setSaveSuccess(listName);
        setTimeout(() => setSaveSuccess(null), 2000);
        await fetchLists();
      } catch (err) {
        console.error('Failed to add to list:', err);
      } finally {
        setSaving(false);
      }
    },
    [selectedIds, fetchLists]
  );

  const handleLoadList = useCallback(
    (list: ProspectList) => {
      onLoadList(list);
    },
    [onLoadList]
  );

  return (
    <div className="flex items-center gap-2">
      {/* Save to List dropdown */}
      <DropdownMenu
        onOpenChange={(open) => {
          if (open) {
            fetchLists();
            setShowCreate(false);
            setNewListName('');
          }
        }}
      >
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            disabled={selectedIds.size === 0 || saving}
            className="gap-1.5"
          >
            {saving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : saveSuccess ? (
              <Check className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <BookmarkPlus className="w-3.5 h-3.5" />
            )}
            {saveSuccess ? `Saved to ${saveSuccess}` : 'Save to List'}
            <ChevronDown className="w-3 h-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel className="text-xs">
            Save {selectedIds.size} {selectedIds.size === 1 ? 'contact' : 'contacts'} to...
          </DropdownMenuLabel>
          <DropdownMenuSeparator />

          {/* Create new list */}
          {showCreate ? (
            <div className="p-2">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleCreateList(newListName);
                }}
                className="flex gap-1.5"
              >
                <Input
                  placeholder="List name..."
                  value={newListName}
                  onChange={(e) => setNewListName(e.target.value)}
                  className="h-7 text-xs"
                  autoFocus
                />
                <Button
                  type="submit"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  disabled={!newListName.trim() || saving}
                >
                  {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Create'}
                </Button>
              </form>
            </div>
          ) : (
            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setShowCreate(true);
              }}
              className="gap-2 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              Create New List
            </DropdownMenuItem>
          )}

          {lists.length > 0 && <DropdownMenuSeparator />}

          {/* Existing lists */}
          {lists.map((list) => (
            <DropdownMenuItem
              key={list.id}
              onSelect={() => handleAddToExisting(list.id, list.name)}
              className="cursor-pointer"
            >
              <div className="flex items-center justify-between w-full">
                <span className="truncate">{list.name}</span>
                <span className="text-xs text-muted-foreground ml-2 shrink-0">
                  {list.member_count ?? 0}
                </span>
              </div>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Load List dropdown */}
      <DropdownMenu onOpenChange={(open) => { if (open) fetchLists(); }}>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="gap-1.5">
            <FolderOpen className="w-3.5 h-3.5" />
            Load List
            <ChevronDown className="w-3 h-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel className="text-xs">Saved Lists</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {lists.length === 0 ? (
            <div className="px-2 py-3 text-xs text-muted-foreground text-center">
              No saved lists yet
            </div>
          ) : (
            lists.map((list) => (
              <DropdownMenuItem
                key={list.id}
                onSelect={() => handleLoadList(list)}
                className="cursor-pointer"
              >
                <div className="flex items-center justify-between w-full">
                  <div className="min-w-0">
                    <div className="truncate font-medium">{list.name}</div>
                    {list.description && (
                      <div className="text-xs text-muted-foreground truncate">
                        {list.description}
                      </div>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground ml-2 shrink-0">
                    {list.member_count ?? 0} contacts
                  </span>
                </div>
              </DropdownMenuItem>
            ))
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
