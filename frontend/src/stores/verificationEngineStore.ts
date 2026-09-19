import { create } from 'zustand';
import type { CatalogVerificationResult, KeywordSearchResult, CoverageCheckResult } from '../types';

interface VerificationEngineState {
  sessionId: string | null;
  isRunning: boolean;
  catalogResult: CatalogVerificationResult | null;
  searchResult: KeywordSearchResult | null;
  coverageResult: CoverageCheckResult | null;
  error: string | null;
  setSessionId: (id: string | null) => void;
  setIsRunning: (val: boolean) => void;
  setCatalogResult: (result: CatalogVerificationResult | null) => void;
  setSearchResult: (result: KeywordSearchResult | null) => void;
  setCoverageResult: (result: CoverageCheckResult | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useVerificationEngineStore = create<VerificationEngineState>((set) => ({
  sessionId: null,
  isRunning: false,
  catalogResult: null,
  searchResult: null,
  coverageResult: null,
  error: null,
  setSessionId: (id) => set({ sessionId: id }),
  setIsRunning: (val) => set({ isRunning: val }),
  setCatalogResult: (result) => set({ catalogResult: result }),
  setSearchResult: (result) => set({ searchResult: result }),
  setCoverageResult: (result) => set({ coverageResult: result }),
  setError: (error) => set({ error }),
  reset: () => set({ sessionId: null, isRunning: false, catalogResult: null, searchResult: null, coverageResult: null, error: null }),
}));
