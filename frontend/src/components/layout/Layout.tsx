import React, { useState } from 'react';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen min-h-[100dvh] bg-obsidian-950 text-slate-100 font-sans antialiased selection:bg-amber-ops selection:text-obsidian-950">
      {/* Mobile Backdrop Overlay */}
      {mobileSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-30 md:hidden"
          onClick={() => setMobileSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Fixed Static Sidebar */}
      <Sidebar 
        isOpen={mobileSidebarOpen} 
        onClose={() => setMobileSidebarOpen(false)} 
      />

      {/* Main Content Layout with Desktop Left Offset */}
      <div className="flex flex-col min-h-screen min-h-[100dvh] md:pl-60 transition-[padding] duration-200">
        <Navbar onToggleSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)} />
        <main className="flex-1 p-4 sm:p-6 bg-obsidian-950 bg-grid-pattern/30 min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
};
