import { createSupabaseClient } from '@/lib/supabase'
import { NextRequest } from 'next/server'

const PROJECT_ID = 'uptogether'

export async function GET() {
  try {
    const supabase = createSupabaseClient()

    const { data, error } = await supabase
      .from('project_tasks')
      .select('*')
      .eq('project_id', PROJECT_ID)
      .order('section')
      .order('sort_order')

    if (error) throw new Error(`DB error: ${error.message}`)

    const grouped: Record<string, typeof data> = {}
    for (const task of data || []) {
      const section = task.section || 'Uncategorized'
      if (!grouped[section]) grouped[section] = []
      grouped[section].push(task)
    }

    return Response.json({ tasks: data || [], grouped })
  } catch (error: unknown) {
    console.error('Tasks GET error:', error)
    return Response.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch tasks' },
      { status: 500 }
    )
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const supabase = createSupabaseClient()

    const { data, error } = await supabase
      .from('project_tasks')
      .insert({
        project_id: PROJECT_ID,
        section: body.section,
        subsection: body.subsection || null,
        title: body.title,
        description: body.description || null,
        status: body.status || 'todo',
        owner: body.owner || null,
        due_date: body.due_date || null,
        sort_order: body.sort_order || 0,
        notes: body.notes || null,
      })
      .select()
      .single()

    if (error) throw new Error(`DB error: ${error.message}`)

    return Response.json({ task: data }, { status: 201 })
  } catch (error: unknown) {
    console.error('Tasks POST error:', error)
    return Response.json(
      { error: error instanceof Error ? error.message : 'Failed to create task' },
      { status: 500 }
    )
  }
}

export async function PATCH(req: NextRequest) {
  try {
    const body = await req.json()
    const { id, ...updates } = body

    if (!id) {
      return Response.json({ error: 'Task id is required' }, { status: 400 })
    }

    const supabase = createSupabaseClient()

    const allowedFields = ['status', 'notes', 'owner', 'title', 'description', 'due_date']
    const filtered: Record<string, unknown> = { updated_at: new Date().toISOString() }
    for (const key of allowedFields) {
      if (key in updates) filtered[key] = updates[key]
    }

    const { data, error } = await supabase
      .from('project_tasks')
      .update(filtered)
      .eq('id', id)
      .eq('project_id', PROJECT_ID)
      .select()
      .single()

    if (error) throw new Error(`DB error: ${error.message}`)

    return Response.json({ task: data })
  } catch (error: unknown) {
    console.error('Tasks PATCH error:', error)
    return Response.json(
      { error: error instanceof Error ? error.message : 'Failed to update task' },
      { status: 500 }
    )
  }
}
