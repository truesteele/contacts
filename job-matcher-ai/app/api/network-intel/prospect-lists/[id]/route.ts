import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export const runtime = 'edge';

const MEMBER_CONTACT_COLS =
  'id, list_id, contact_id, outreach_status, notes, added_at';

const CONTACT_COLS =
  'id, first_name, last_name, company, position, city, state, email, linkedin_url, headline, ' +
  'ai_proximity_score, ai_proximity_tier, ai_capacity_score, ai_capacity_tier, ' +
  'ai_kindora_prospect_score, ai_kindora_prospect_type, ai_outdoorithm_fit';

/**
 * GET /api/network-intel/prospect-lists/[id]
 * Returns list details with all members joined with contact data.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    // Fetch the list
    const { data: list, error: listError } = await supabase
      .from('prospect_lists')
      .select('id, name, description, created_at, updated_at')
      .eq('id', id)
      .single();

    if (listError || !list) {
      return NextResponse.json({ error: 'List not found' }, { status: 404 });
    }

    // Fetch members
    const { data: members, error: memberError } = await supabase
      .from('prospect_list_members')
      .select(MEMBER_CONTACT_COLS)
      .eq('list_id', id)
      .order('added_at', { ascending: false });

    if (memberError) throw new Error(`Failed to fetch members: ${memberError.message}`);

    const memberList = members || [];

    // Fetch contact data for all members
    const contactIds = memberList.map((m: any) => m.contact_id);
    let contactMap = new Map<number, any>();

    if (contactIds.length > 0) {
      const { data: contacts, error: contactError } = await supabase
        .from('contacts')
        .select(CONTACT_COLS)
        .in('id', contactIds);

      if (contactError) throw new Error(`Failed to fetch contacts: ${contactError.message}`);

      for (const c of contacts || []) {
        contactMap.set((c as any).id, c);
      }
    }

    // Join member data with contact data
    const membersWithContacts = memberList.map((m: any) => ({
      ...m,
      contact: contactMap.get(m.contact_id) || null,
    }));

    return NextResponse.json({
      ...list,
      member_count: membersWithContacts.length,
      members: membersWithContacts,
    });
  } catch (err: any) {
    console.error('[Prospect List GET] Error:', err);
    return NextResponse.json(
      { error: err.message || 'Failed to fetch prospect list' },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/network-intel/prospect-lists/[id]
 * Update list metadata, add/remove members, update member outreach_status.
 * Body: {
 *   name?: string,
 *   description?: string,
 *   add_contacts?: number[],
 *   remove_contacts?: number[],
 *   update_status?: { contact_id: number, status: string }[]
 * }
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();

    // Verify list exists
    const { data: existing, error: existError } = await supabase
      .from('prospect_lists')
      .select('id')
      .eq('id', id)
      .single();

    if (existError || !existing) {
      return NextResponse.json({ error: 'List not found' }, { status: 404 });
    }

    const { name, description, add_contacts, remove_contacts, update_status } = body as {
      name?: string;
      description?: string;
      add_contacts?: number[];
      remove_contacts?: number[];
      update_status?: { contact_id: number; status: string }[];
    };

    const errors: string[] = [];

    // Update list metadata if provided
    if (name !== undefined || description !== undefined) {
      const updates: Record<string, any> = {};
      if (name !== undefined) {
        if (typeof name !== 'string' || name.trim().length === 0) {
          return NextResponse.json(
            { error: 'Name must be a non-empty string' },
            { status: 400 }
          );
        }
        updates.name = name.trim();
      }
      if (description !== undefined) {
        updates.description = description?.trim() || null;
      }

      const { error: updateError } = await supabase
        .from('prospect_lists')
        .update(updates)
        .eq('id', id);

      if (updateError) errors.push(`Failed to update metadata: ${updateError.message}`);
    }

    // Add contacts
    if (add_contacts && add_contacts.length > 0) {
      const members = add_contacts.map((contact_id) => ({
        list_id: id,
        contact_id,
      }));

      // Use upsert to skip duplicates (unique constraint on list_id + contact_id)
      const { error: addError } = await supabase
        .from('prospect_list_members')
        .upsert(members, { onConflict: 'list_id,contact_id', ignoreDuplicates: true });

      if (addError) errors.push(`Failed to add contacts: ${addError.message}`);
    }

    // Remove contacts
    if (remove_contacts && remove_contacts.length > 0) {
      const { error: removeError } = await supabase
        .from('prospect_list_members')
        .delete()
        .eq('list_id', id)
        .in('contact_id', remove_contacts);

      if (removeError) errors.push(`Failed to remove contacts: ${removeError.message}`);
    }

    // Update outreach statuses
    if (update_status && update_status.length > 0) {
      const validStatuses = [
        'not_contacted', 'reached_out', 'responded',
        'meeting_scheduled', 'committed', 'declined',
      ];

      for (const { contact_id, status } of update_status) {
        if (!validStatuses.includes(status)) {
          errors.push(`Invalid status "${status}" for contact ${contact_id}`);
          continue;
        }

        const { error: statusError } = await supabase
          .from('prospect_list_members')
          .update({ outreach_status: status })
          .eq('list_id', id)
          .eq('contact_id', contact_id);

        if (statusError) errors.push(`Failed to update status for contact ${contact_id}: ${statusError.message}`);
      }
    }

    // Fetch updated list to return
    const { data: updatedList, error: fetchError } = await supabase
      .from('prospect_lists')
      .select('id, name, description, created_at, updated_at')
      .eq('id', id)
      .single();

    if (fetchError) throw new Error(`Failed to fetch updated list: ${fetchError.message}`);

    // Get updated member count
    const { data: memberCount, error: countError } = await supabase
      .from('prospect_list_members')
      .select('id')
      .eq('list_id', id);

    return NextResponse.json({
      ...updatedList,
      member_count: countError ? 0 : (memberCount || []).length,
      ...(errors.length > 0 ? { warnings: errors } : {}),
    });
  } catch (err: any) {
    console.error('[Prospect List PATCH] Error:', err);
    return NextResponse.json(
      { error: err.message || 'Failed to update prospect list' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/network-intel/prospect-lists/[id]
 * Delete a prospect list. Members are CASCADE deleted.
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    // Verify list exists
    const { data: existing, error: existError } = await supabase
      .from('prospect_lists')
      .select('id, name')
      .eq('id', id)
      .single();

    if (existError || !existing) {
      return NextResponse.json({ error: 'List not found' }, { status: 404 });
    }

    // Delete the list (CASCADE removes members)
    const { error: deleteError } = await supabase
      .from('prospect_lists')
      .delete()
      .eq('id', id);

    if (deleteError) throw new Error(`Failed to delete list: ${deleteError.message}`);

    return NextResponse.json({
      deleted: true,
      id,
      name: (existing as any).name,
    });
  } catch (err: any) {
    console.error('[Prospect List DELETE] Error:', err);
    return NextResponse.json(
      { error: err.message || 'Failed to delete prospect list' },
      { status: 500 }
    );
  }
}
