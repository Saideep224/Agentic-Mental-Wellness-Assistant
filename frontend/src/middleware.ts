import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const protectedRoutes = ['/chat', '/dashboard', '/onboarding'];

// Routes that should redirect to /chat if user is already logged in
const authRoutes = ['/login'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check for auth token in cookies (from next-auth) or custom header
  const sessionToken =
    request.cookies.get('next-auth.session-token')?.value ||
    request.cookies.get('__Secure-next-auth.session-token')?.value;

  // For protected routes, redirect to login if no session
  if (protectedRoutes.some((route) => pathname.startsWith(route))) {
    // We'll rely on client-side auth checks since we're using localStorage tokens
    // The middleware here is a fallback for next-auth sessions
    // Client-side components will handle the redirect for token-based auth
    return NextResponse.next();
  }

  // We delegate all login and auth redirection logic to the client-side AuthProvider
  // to ensure onboarding verification completes correctly before routing to chat.

  return NextResponse.next();
}

export const config = {
  matcher: ['/chat/:path*', '/dashboard/:path*', '/onboarding/:path*', '/login'],
};
