import { useCallback, useEffect, useRef, useState } from "react";
import { api, type AddressSuggestion } from "../api";
import { addressSearchIntent } from "../addressSearch";

const suggestionCache = new Map<string, AddressSuggestion[]>();
const SUGGESTION_CACHE_MAX = 200;

function cacheSuggestions(key: string, value: AddressSuggestion[]) {
  if (suggestionCache.size >= SUGGESTION_CACHE_MAX) {
    const oldest = suggestionCache.keys().next().value;
    if (oldest !== undefined) suggestionCache.delete(oldest);
  }
  suggestionCache.set(key, value);
}

async function searchAddressWithGuestBootstrap(text: string, limit: number) {
  const result = await api.searchAddress(text, limit);
  if (result.kind !== "auth") return result;

  const guest = await api.guestSession();
  if (guest.kind !== "ok") return result;

  return api.searchAddress(text, limit);
}

export function useAddressSuggestions(limit = 6) {
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([]);
  const [suggestionIndex, setSuggestionIndex] = useState(-1);
  const timer = useRef<number | undefined>(undefined);
  const sequence = useRef(0);

  const closeSuggestions = useCallback(() => {
    window.clearTimeout(timer.current);
    sequence.current += 1;
    setSuggestions([]);
    setSuggestionIndex(-1);
  }, []);

  const queueSuggestions = useCallback((text: string) => {
    window.clearTimeout(timer.current);
    const trimmed = text.trim();
    if (!addressSearchIntent(trimmed)) {
      closeSuggestions();
      return;
    }

    const key = trimmed.toLowerCase();
    const cached = suggestionCache.get(key);
    if (cached) {
      sequence.current += 1;
      setSuggestions(cached.slice(0, limit));
      setSuggestionIndex(-1);
      return;
    }

    timer.current = window.setTimeout(async () => {
      const seq = ++sequence.current;
      const result = await searchAddressWithGuestBootstrap(trimmed, limit);
      if (seq !== sequence.current) return;
      const list = result.kind === "ok"
        ? result.data.items.map((item) => ({ address: item.address, gnaf_pid: item.gnaf_pid }))
        : [];
      if (result.kind === "ok") cacheSuggestions(key, list);
      setSuggestions(list.slice(0, limit));
      setSuggestionIndex(-1);
    }, 120);
  }, [closeSuggestions, limit]);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  return {
    suggestions,
    suggestionIndex,
    setSuggestionIndex,
    closeSuggestions,
    queueSuggestions,
  };
}
