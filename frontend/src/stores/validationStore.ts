import { create } from 'zustand'
import { ScanProgress, ValidationProgress, RequirementResult } from '../types'

interface ValidationState {
  scanProgress: ScanProgress | null;
  validationProgress: ValidationProgress | null;
  results: RequirementResult[];
  isScanning: boolean;
  isValidating: boolean;
  setScanProgress: (progress: ScanProgress | null) => void;
  setValidationProgress: (progress: ValidationProgress | null) => void;
  setResults: (results: RequirementResult[]) => void;
  setIsScanning: (val: boolean) => void;
  setIsValidating: (val: boolean) => void;
  reset: () => void;
}

export const useValidationStore = create<ValidationState>((set) => ({
  scanProgress: null,
  validationProgress: null,
  results: [],
  isScanning: false,
  isValidating: false,
  setScanProgress: (progress) => set({ scanProgress: progress }),
  setValidationProgress: (progress) => set({ validationProgress: progress }),
  setResults: (results) => set({ results }),
  setIsScanning: (val) => set({ isScanning: val }),
  setIsValidating: (val) => set({ isValidating: val }),
  reset: () => set({ scanProgress: null, validationProgress: null, results: [], isScanning: false, isValidating: false }),
}))
