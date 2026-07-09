'use client';

import { useEffect } from 'react';
import { usePathname, useSearchParams, useRouter } from 'next/navigation';
import NProgress from 'nprogress';

// Configure NProgress
NProgress.configure({
  showSpinner: false,
  speed: 500,
  minimum: 0.1,
  easing: 'ease',
  trickleSpeed: 200,
});

export function TopLoader() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();

  // --- Run NProgress on initial page load (refresh) ---
  useEffect(() => {
    NProgress.start();
    NProgress.done(); // hydration completes almost instantly
  }, []);

  // --- Intercept <a> clicks ---
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const link = target.closest('a') as HTMLAnchorElement | null;

      if (link && link.href.startsWith(window.location.origin)) {
        NProgress.start();
      }
    };

    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  // --- Intercept router.push / router.replace ---
  useEffect(() => {
    const originalPush = router.push;
    const originalReplace = router.replace;

    router.push = (...args: Parameters<typeof router.push>) => {
      NProgress.start();
      return originalPush(...args);
    };

    router.replace = (...args: Parameters<typeof router.replace>) => {
      NProgress.start();
      return originalReplace(...args);
    };

    return () => {
      router.push = originalPush;
      router.replace = originalReplace;
    };
  }, [router]);

  // --- Finish NProgress on route change complete ---
  useEffect(() => {
    NProgress.done();
  }, [pathname, searchParams]);

  return null;
}