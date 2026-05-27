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
  const { logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setMounted(true);
  }, []);

  const token = mounted ? getToken() : null;
  const user = mounted ? getStoredUser() : null;
  const isLoggedIn = mounted && !!token;

  const navLinks = [
    { href: '/chat', label: 'Chat', icon: MessageCircle },
    { href: '/knowing-me', label: 'Knowing Me', icon: Heart },
    { href: '/dashboard', label: 'Dashboard', icon: BarChart3 },
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
        className="mx-4 mt-4 rounded-2xl glass-card"
        style={{
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
        }}
      >
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <EsonaLogo size={32} showParticles={false} glowIntensity="low" />
            <span
              className="text-xl font-bold glow-text"
              style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
            >
              Esona
            </span>
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center gap-1">
            {isLoggedIn &&
              navLinks.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={cn(
                      'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300',
                      isActive
                        ? 'text-sky-400'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    )}
                    style={
                      isActive
                        ? {
                            background: 'rgba(56, 189, 248, 0.1)',
                            boxShadow: 'inset 0 0 10px rgba(56, 189, 248, 0.1)',
                          }
                        : {}
                    }
                  >
                    <link.icon size={16} />
                    {link.label}
                  </Link>
                );
              })}
          </div>

          {/* Right side - User/Login */}
          <div className="hidden md:flex items-center gap-3">
            {isLoggedIn ? (
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsProfileModalOpen(true)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass-card hover:border-[rgba(56,189,248,0.3)] transition-all duration-300 cursor-pointer"
                >
                  <UserAvatar
                    size={28}
                    avatarUrl={user?.avatarUrl}
                    name={user?.name}
                    glow={false}
                    enableHover={false}
                  />
                  <span className="text-sm font-medium text-slate-300">
                    {user?.name || 'User'}
                  </span>
                </button>
                <button
                  onClick={handleLogout}
                  className="p-2 rounded-xl transition-all duration-300 hover:bg-white/5 cursor-pointer"
                  style={{ color: 'var(--text-muted)' }}
                  title="Sign out"
                >
                  <LogOut size={16} />
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="gradient-btn px-5 py-2 text-sm rounded-xl flex items-center gap-2"
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
