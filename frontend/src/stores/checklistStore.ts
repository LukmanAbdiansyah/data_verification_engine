import { create } from 'zustand';
import { Requirement } from '../types';

interface ChecklistState {
  requirements: Requirement[];
  confirmed: boolean;
  columnMapping: Record<string, string>;
  mappingRequired: boolean;
  columnOptions: string[];
  rawRows: any[];
  setRawRows: (rows: any[]) => void;
  setRequirements: (reqs: Requirement[]) => void;
  updateRequirement: (id: string, req: Partial<Requirement>) => void;
  addRequirement: (req: Requirement) => void;
  deleteRequirement: (id: string) => void;
  duplicateRequirement: (id: string) => void;
  setConfirmed: (confirmed: boolean) => void;
  setColumnMapping: (mapping: Record<string, string>) => void;
}

export const useChecklistStore = create<ChecklistState>((set) => ({
  requirements: [],
  confirmed: false,
  columnMapping: {},
  mappingRequired: false,
  columnOptions: ['progress', 'format'],
  rawRows: [],
  setRawRows: (rows) => set({ rawRows: rows }),
  setRequirements: (requirements) => set({ requirements }),
  updateRequirement: (id, updated) => set((state) => ({
    requirements: state.requirements.map(r => r.id === id ? { ...r, ...updated } : r)
  })),
  addRequirement: (req) => set((state) => ({ requirements: [...state.requirements, req] })),
  deleteRequirement: (id) => set((state) => ({ requirements: state.requirements.filter(r => r.id !== id) })),
  duplicateRequirement: (id) => set((state) => {
    const req = state.requirements.find(r => r.id === id);
    if (!req) return state;
    const newId = Math.random().toString(36).substring(7);
    const dup: Requirement = {
      ...req,
      id: newId,
      req_id: `REQ-${String(state.requirements.length + 1).padStart(3, '0')}`,
      source_row: state.requirements.length + 1,
      validation_note: 'Duplicate Requirement',
    };
    return { requirements: [...state.requirements, dup] };
  }),
  setConfirmed: (confirmed) => set({ confirmed }),
  setColumnMapping: (columnMapping) => set({ columnMapping }),
}));
