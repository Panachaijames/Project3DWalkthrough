// document.title per screen (DESIGN.md 15.1: `Projects · Walkthrough`, `<name> · v<n> · Walkthrough`).
import { useEffect } from 'react';

export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = title;
  }, [title]);
}
