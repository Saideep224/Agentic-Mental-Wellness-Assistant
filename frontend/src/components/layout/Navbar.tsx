'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, BarChart3, Heart, Menu, X, LogOut, User as UserIcon } from 'lucide-react';
import { cn } from '@/utils';
import { getToken, getStoredUser, clearAuth } from '@/api';
import ProfileModal from '@/components/layout/ProfileModal';
import { useAuth } from '@/providers/AuthProvider';
import EsonaLogo from '@/components/layout/EsonaLogo';
import UserAvatar from '@/components/layout/UserAvatar';

export default function Navbar() {
  const { user, token, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setMounted(true);
  }, []);

  const isLoggedIn = mounted && !!token && !!user;

  const navLinks = [
    { href: '/chat', label: 'Chat', icon: MessageCircle },
    { href: '/knowing-me', label: 'Knowing Me', icon: Heart },
    { href: '/dashboard', label: 'My Growth', icon: BarChart3 },
  ];

  const handleLogout = async () => {
    await logout();
  };

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="fixed top-0 left-0 right-0 z-50"
    >
      <div
        className="border-b border-white/5 bg-[#040614]/65 backdrop-blur-md transition-colors duration-300"
      >
        <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <EsonaLogo size={28} showParticles={false} glowIntensity="low" />
            <span
              className="text-lg font-semibold tracking-wider text-slate-200"
              style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
            >
              Esona
            </span>
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center gap-6">
            {!mounted ? (
              <div className="h-4 w-64 bg-white/5 rounded animate-pulse" />
            ) : (
              isLoggedIn &&
              navLinks.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={cn(
                      'text-xs uppercase tracking-widest font-medium transition-all duration-300 relative py-1.5',
                      isActive
                        ? 'text-cyan-400 font-semibold'
                        : 'text-[#8B9BB8] hover:text-white'
                    )}
                  >
                    {link.label}
                    {isActive && (
                      <motion.div
                        layoutId="navUnderline"
                        className="absolute bottom-0 left-0 right-0 h-[2px] bg-cyan-400/80 rounded-full"
                        style={{
                          boxShadow: '0 0 8px rgba(34, 211, 238, 0.6)'
                        }}
                      />
                    )}
                  </Link>
                );
              })
            )}
          </div>

          {/* Right side - User/Login */}
          <div className="hidden md:flex items-center gap-4">
            {!mounted ? (
              <div className="h-8 w-24 bg-white/5 rounded animate-pulse" />
            ) : isLoggedIn ? (
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setIsProfileModalOpen(true)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/5 transition-all duration-300 cursor-pointer text-xs uppercase tracking-widest text-slate-300 font-medium"
                >
                  <UserAvatar
                    size={24}
                    avatarUrl={user?.avatarUrl}
                    name={user?.name}
                    glow={false}
                    enableHover={false}
                  />
                  <span>
                    {user?.name || 'User'}
                  </span>
                </button>
                <button
                  onClick={handleLogout}
                  className="p-2 rounded-lg transition-all duration-300 hover:bg-white/5 cursor-pointer text-[#8B9BB8] hover:text-white"
                  title="Sign out"
                >
                  <LogOut size={15} />
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="text-xs uppercase tracking-widest px-4 py-2 rounded-lg border border-white/10 hover:border-cyan-400/30 text-slate-200 transition-all duration-300"
              >
                Get Started
              </Link>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-xl transition-colors cursor-pointer"
            style={{ color: 'var(--text-secondary)' }}
          >
            {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isMobileMenuOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="md:hidden overflow-hidden border-t"
              style={{ borderColor: 'var(--glass-border)' }}
            >
              <div className="px-6 py-4 flex flex-col gap-2">
                {isLoggedIn &&
                  navLinks.map((link) => {
                    const isActive = pathname === link.href;
                    return (
                      <Link
                        key={link.href}
                        href={link.href}
                        onClick={() => setIsMobileMenuOpen(false)}
                        className={cn(
                          'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all',
                          isActive
                            ? 'text-[var(--accent-cyan)]'
                            : 'text-[var(--text-secondary)]'
                        )}
                        style={
                          isActive
                            ? { background: 'rgba(56, 189, 248, 0.1)' }
                            : {}
                        }
                      >
                        <link.icon size={18} />
                        {link.label}
                      </Link>
                    );
                  })}

                {isLoggedIn ? (
                  <>
                    <button
                      onClick={() => {
                        setIsMobileMenuOpen(false);
                        setIsProfileModalOpen(true);
                      }}
                      className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-300 cursor-pointer"
                    >
                      <UserIcon size={18} className="text-sky-400" />
                      View Profile
                    </button>
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium cursor-pointer w-full text-left"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      <LogOut size={18} />
                      Sign out
                    </button>
                  </>
                ) : (
                  <Link
                    href="/login"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="gradient-btn px-5 py-3 text-sm text-center rounded-xl"
                  >
                    Get Started
                  </Link>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      {/* Profile Modal */}
      <ProfileModal isOpen={isProfileModalOpen} onClose={() => setIsProfileModalOpen(false)} />
    </motion.nav>
  );
}
