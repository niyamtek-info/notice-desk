// hooks/usePageTitle.ts
'use client';

import { useEffect } from 'react';
import { useTitle } from '@/context/TitleContext';

const DEFAULT_TITLE = 'My Application';

export default function usePageTitle(title?: string) {
  const { setTitle } = useTitle();

  useEffect(() => {
    const finalTitle = title || DEFAULT_TITLE;
    setTitle(finalTitle);
    document.title = finalTitle;

    return () => {
      setTitle(DEFAULT_TITLE);
      document.title = DEFAULT_TITLE;
    };
  }, [title, setTitle]);
}
