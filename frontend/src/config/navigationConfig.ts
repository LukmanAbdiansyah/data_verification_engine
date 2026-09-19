import { Activity, LayoutDashboard, ClipboardList, FolderOpen, PlayCircle, Table2, Clock, Settings, ShieldCheck, FileSpreadsheet, Search, CheckSquare, BookOpen, Layers, Waves, FileText, type LucideIcon } from 'lucide-react';

export interface NavItem {
  path: string;
  icon: LucideIcon;
  label: string;
}

export interface AppModule {
  id: string;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
  basePath: string;
  navItems: NavItem[];
}

export const modules: AppModule[] = [
  {
    id: 'seismic',
    label: 'Seismic Checker',
    shortLabel: 'Seismic',
    icon: Activity,
    basePath: '/seismic',
    navItems: [
      { path: '/seismic', icon: LayoutDashboard, label: 'Dashboard' },
      { path: '/seismic/checklist', icon: ClipboardList, label: 'Checklist' },
      { path: '/seismic/repository', icon: FolderOpen, label: 'Repository' },
      { path: '/seismic/validation', icon: PlayCircle, label: 'Validation' },
      { path: '/seismic/results', icon: Table2, label: 'Results' },
      { path: '/seismic/history', icon: Clock, label: 'History' },
    ],
  },
  {
    id: 'verification',
    label: 'Verification Engine',
    shortLabel: 'Verify',
    icon: ShieldCheck,
    basePath: '/verification',
    navItems: [
      { path: '/verification', icon: LayoutDashboard, label: 'Overview' },
      { path: '/verification/catalog', icon: FileSpreadsheet, label: 'Catalog Check' },
      { path: '/verification/search', icon: Search, label: 'Keyword Search' },
      { path: '/verification/coverage', icon: CheckSquare, label: 'Coverage Check' },
    ],
  },
  {
    id: 'catalog',
    label: 'Catalog Generator',
    shortLabel: 'Catalog',
    icon: BookOpen,
    basePath: '/catalog',
    navItems: [
      { path: '/catalog', icon: LayoutDashboard, label: 'Overview' },
      { path: '/catalog/seismic', icon: Waves, label: 'Seismic Catalog' },
      { path: '/catalog/well', icon: FileText, label: 'Well Catalog' },
    ],
  },
];

export const settingsNav: NavItem = {
  path: '/settings',
  icon: Settings,
  label: 'Settings',
};

/**
 * Find the active module based on the current pathname.
 */
export function findActiveModule(pathname: string): AppModule | undefined {
  return modules.find((m) => pathname.startsWith(m.basePath));
}
