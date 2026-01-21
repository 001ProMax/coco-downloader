'use client';

import Link from "next/link";
import { Music, User, Github, Sun, Moon } from "lucide-react";
import { useState, useEffect, MouseEvent } from "react";
import { useTheme } from "next-themes";
import DeveloperPanel from "./DeveloperPanel";

export function Navbar() {
  const [showDevPanel, setShowDevPanel] = useState(false);
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
     
    setMounted(true);
  }, []);

  const toggleTheme = (event: MouseEvent<HTMLButtonElement>) => {
    const isDark = resolvedTheme === 'dark';
    const newTheme = isDark ? 'light' : 'dark';

    // Check if View Transitions API is supported
    if (!document.startViewTransition) {
      setTheme(newTheme);
      return;
    }

    const x = event.clientX;
    const y = event.clientY;
    const endRadius = Math.hypot(
      Math.max(x, innerWidth - x),
      Math.max(y, innerHeight - y)
    );

    const transition = document.startViewTransition(() => {
      setTheme(newTheme);
    });

    transition.ready.then(() => {
      const clipPath = [
        `circle(0px at ${x}px ${y}px)`,
        `circle(${endRadius}px at ${x}px ${y}px)`,
      ];

      document.documentElement.animate(
        {
          clipPath: clipPath,
        },
        {
          duration: 500,
          easing: "ease-in",
          pseudoElement: "::view-transition-new(root)",
        }
      );
    });
  };

  return (
    <>
      <nav className="fixed top-[37px] left-0 right-0 h-16 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-sky-100 dark:border-slate-800 z-50 px-4 md:px-8 flex items-center justify-between transition-colors duration-300">
        <Link href="/" className="flex items-center gap-2 group">
          <img src="/images/cherry-logo.svg" alt="Logo" className="h-10 w-auto transition-transform" />
        </Link>
        
        <div className="flex items-center gap-4">
          <Link 
            href="/" 
            className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-sky-500 dark:hover:text-sky-400 transition-colors"
          >
            首页
          </Link>
          
          <a 
            href="https://github.com/markcxx/coco-downloader" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-slate-400 dark:text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
          >
            <Github className="w-5 h-5" />
          </a>

          {mounted && (
            <button
              onClick={toggleTheme}
              className="p-2 text-slate-400 dark:text-slate-500 hover:text-sky-500 dark:hover:text-sky-400 hover:bg-sky-50 dark:hover:bg-slate-800 rounded-full transition-all duration-300 cursor-pointer"
              aria-label="Toggle theme"
            >
              {resolvedTheme === 'dark' ? (
                <Moon className="w-5 h-5" />
              ) : (
                <Sun className="w-5 h-5" />
              )}
            </button>
          )}
        </div>
      </nav>

      <DeveloperPanel open={showDevPanel} onClose={() => setShowDevPanel(false)} />
    </>
  );
}
