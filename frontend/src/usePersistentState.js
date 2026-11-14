import { useEffect, useState } from "react";

// Like useState, but survives a page refresh (kept in sessionStorage, so it is gone when the tab closes).
export default function usePersistentState(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const saved = sessionStorage.getItem(key);
      return saved ? JSON.parse(saved) : initial;
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    try {
      if (value === null || value === undefined) sessionStorage.removeItem(key);
      else sessionStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage unavailable: the app still works, it just forgets on refresh */
    }
  }, [key, value]);

  return [value, setValue];
}