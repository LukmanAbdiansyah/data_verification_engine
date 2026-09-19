import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { DashboardPage } from '@/pages/DashboardPage';
import { ChecklistPage } from '@/pages/ChecklistPage';
import { RepositoryPage } from '@/pages/RepositoryPage';
import { ValidationPage } from '@/pages/ValidationPage';
import { ResultsPage } from '@/pages/ResultsPage';
import { HistoryPage } from '@/pages/HistoryPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { ReviewPage } from '@/pages/ReviewPage';
import { VerificationOverviewPage } from '@/pages/verification/VerificationOverviewPage';
import { CatalogCheckPage } from '@/pages/verification/CatalogCheckPage';
import { KeywordSearchPage } from '@/pages/verification/KeywordSearchPage';
import { CoverageCheckPage } from '@/pages/verification/CoverageCheckPage';
import { CatalogOverviewPage } from '@/pages/catalog/CatalogOverviewPage';
import { SeismicCatalogPage } from '@/pages/catalog/SeismicCatalogPage';
import { WellCatalogPage } from '@/pages/catalog/WellCatalogPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        {/* Default redirect to seismic module */}
        <Route index element={<Navigate to="/seismic" replace />} />

        {/* Seismic Checker module */}
        <Route path="seismic" element={<DashboardPage />} />
        <Route path="seismic/checklist" element={<ChecklistPage />} />
        <Route path="seismic/repository" element={<RepositoryPage />} />
        <Route path="seismic/validation" element={<ValidationPage />} />
        <Route path="seismic/results" element={<ResultsPage />} />
        <Route path="seismic/history" element={<HistoryPage />} />
        <Route path="seismic/review" element={<ReviewPage />} />

        {/* Verification Engine module */}
        <Route path="verification" element={<VerificationOverviewPage />} />
        <Route path="verification/catalog" element={<CatalogCheckPage />} />
        <Route path="verification/search" element={<KeywordSearchPage />} />
        <Route path="verification/coverage" element={<CoverageCheckPage />} />

        {/* Catalog Generator module */}
        <Route path="catalog" element={<CatalogOverviewPage />} />
        <Route path="catalog/seismic" element={<SeismicCatalogPage />} />
        <Route path="catalog/well" element={<WellCatalogPage />} />

        {/* Aliases for top-level routes */}
        <Route path="results" element={<Navigate to="/seismic/results" replace />} />
        <Route path="checklist" element={<Navigate to="/seismic/checklist" replace />} />
        <Route path="repository" element={<Navigate to="/seismic/repository" replace />} />
        <Route path="validation" element={<Navigate to="/seismic/validation" replace />} />
        <Route path="history" element={<Navigate to="/seismic/history" replace />} />
        <Route path="review" element={<Navigate to="/seismic/review" replace />} />

        {/* Global pages */}
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export default App;
