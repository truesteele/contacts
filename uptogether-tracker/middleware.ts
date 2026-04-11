import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

async function verifyAuthCookie(cookieValue: string, secret: string): Promise<boolean> {
  const encoder = new TextEncoder()
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  )
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode('ut-session'))
  const expected = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
  return cookieValue === expected
}

export async function middleware(request: NextRequest) {
  const isLoginPage = request.nextUrl.pathname === '/login'
  const isAuthApi = request.nextUrl.pathname === '/api/auth'

  if (isLoginPage || isAuthApi) {
    return NextResponse.next()
  }

  const auth = request.cookies.get('ut-auth')
  const sitePassword = process.env.SITE_PASSWORD
  if (auth && sitePassword && (await verifyAuthCookie(auth.value, sitePassword))) {
    return NextResponse.next()
  }

  return NextResponse.redirect(new URL('/login', request.url))
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
