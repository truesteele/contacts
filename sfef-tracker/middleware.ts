import { NextRequest, NextResponse } from 'next/server'

async function verifyAuthCookie(cookieValue: string, secret: string): Promise<boolean> {
  const encoder = new TextEncoder()
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  )
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode('sfef-session'))
  const expected = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
  return cookieValue === expected
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  // Allow login page and auth API
  if (pathname === '/login' || pathname.startsWith('/api/auth')) {
    return NextResponse.next()
  }

  // Check auth cookie with HMAC verification
  const auth = req.cookies.get('sfef-auth')
  const sitePassword = process.env.SITE_PASSWORD
  if (auth && sitePassword && (await verifyAuthCookie(auth.value, sitePassword))) {
    return NextResponse.next()
  }

  // Redirect to login
  const loginUrl = new URL('/login', req.url)
  return NextResponse.redirect(loginUrl)
}

export const config = {
  matcher: [
    /*
     * Match all paths except:
     * - _next/static, _next/image (Next.js internals)
     * - favicon.ico, images, etc.
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)',
  ],
}
