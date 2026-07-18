'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Copy, Check } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  copied: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    copied: false,
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] Uncaught rendering exception:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleCopy = () => {
    if (!this.state.error) return;
    const textToCopy = `Error: ${this.state.error.message}\n\nStack:\n${this.state.error.stack || ''}\n\nComponent Stack:\n${this.state.errorInfo?.componentStack || ''}`;
    navigator.clipboard.writeText(textToCopy);
    this.setState({ copied: true });
    setTimeout(() => this.setState({ copied: false }), 2000);
  };

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <main className="min-h-screen flex items-center justify-center p-4 relative z-50 bg-[#040614]">
          {/* Subtle Ambient glows */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full bg-rose-500/10 blur-[120px]" />
          </div>

          <div 
            className="w-full max-w-2xl rounded-2xl p-6 sm:p-8 relative overflow-hidden"
            style={{
              background: 'rgba(10, 14, 30, 0.75)',
              border: '1px solid rgba(244, 63, 94, 0.25)',
              backdropFilter: 'blur(30px)',
              boxShadow: '0 0 60px rgba(244, 63, 94, 0.05), 0 20px 50px rgba(0, 0, 0, 0.5)',
            }}
          >
            {/* Header */}
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-rose-500/15">
              <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
                <AlertTriangle size={20} />
              </div>
              <div>
                <h2 
                  className="text-lg font-bold text-white tracking-wide"
                  style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
                >
                  Application Rendering Exception
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  A client-side component has crashed.
                </p>
              </div>
            </div>

            {/* Error Message */}
            <div className="mb-5 bg-rose-500/5 border border-rose-500/10 rounded-xl p-4">
              <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider block mb-1">
                Message
              </span>
              <p className="text-sm font-medium text-slate-200 font-mono break-all leading-normal">
                {this.state.error?.name || 'Error'}: {this.state.error?.message || 'Unknown error'}
              </p>
            </div>

            {/* Stack Traces */}
            <div className="space-y-4 mb-6">
              {this.state.error?.stack && (
                <div>
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
                    Error Stack
                  </span>
                  <pre className="text-[11px] font-mono bg-black/40 border border-white/5 rounded-lg p-3 overflow-auto max-h-[160px] text-slate-300 leading-normal whitespace-pre-wrap break-all">
                    {this.state.error.stack}
                  </pre>
                </div>
              )}

              {this.state.errorInfo?.componentStack && (
                <div>
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
                    Component Stack (Trace)
                  </span>
                  <pre className="text-[11px] font-mono bg-black/40 border border-white/5 rounded-lg p-3 overflow-auto max-h-[160px] text-slate-300 leading-normal whitespace-pre-wrap break-all">
                    {this.state.errorInfo.componentStack}
                  </pre>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-end pt-2 border-t border-white/5">
              <button
                onClick={this.handleCopy}
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold border border-white/10 text-slate-300 hover:text-white hover:bg-white/5 transition-all duration-200 cursor-pointer"
              >
                {this.state.copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                {this.state.copied ? 'Copied Details' : 'Copy Exception Details'}
              </button>
              <button
                onClick={this.handleReset}
                className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-[#040614] bg-white hover:bg-slate-200 transition-all duration-200 cursor-pointer"
              >
                <RefreshCw size={14} />
                Reload Application
              </button>
            </div>
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}
