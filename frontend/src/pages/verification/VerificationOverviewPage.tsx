import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FileSpreadsheet, Search, CheckSquare } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useVerificationEngineStore } from '@/stores/verificationEngineStore';
import { Badge } from '@/components/ui/Badge';

export function VerificationOverviewPage() {
  const navigate = useNavigate();
  const { catalogResult, searchResult, coverageResult } = useVerificationEngineStore();

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Verification Engine</h1>
        <p className="text-gray-500 dark:text-gray-400">Pilih alat verifikasi yang ingin Anda gunakan.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="flex flex-col">
          <CardHeader>
            <div className="flex items-center gap-2 mb-2">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <CardTitle>Catalog Check</CardTitle>
            </div>
            <CardDescription className="min-h-[60px]">
              Validasi metadata Excel terhadap file fisik di folder. Mendeteksi file MATCHED, MISSING, DUPLICATE, dan EXTRA.
            </CardDescription>
          </CardHeader>
          <CardFooter className="mt-auto pt-4 border-t dark:border-gray-800">
            <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white" onClick={() => navigate('/verification/catalog')}>
              Open Catalog Check
            </Button>
          </CardFooter>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <div className="flex items-center gap-2 mb-2">
              <div className="p-2 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-lg">
                <Search className="w-6 h-6" />
              </div>
              <CardTitle>Keyword Search</CardTitle>
            </div>
            <CardDescription className="min-h-[60px]">
              Cari file berdasarkan kata kunci pada nama file. Mendukung mode pencarian ANY atau ALL.
            </CardDescription>
          </CardHeader>
          <CardFooter className="mt-auto pt-4 border-t dark:border-gray-800">
            <Button className="w-full bg-green-600 hover:bg-green-700 text-white" onClick={() => navigate('/verification/search')}>
              Open Keyword Search
            </Button>
          </CardFooter>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <div className="flex items-center gap-2 mb-2">
              <div className="p-2 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-lg">
                <CheckSquare className="w-6 h-6" />
              </div>
              <CardTitle>Coverage Check</CardTitle>
            </div>
            <CardDescription className="min-h-[60px]">
              Verifikasi kelengkapan dokumen per subfolder berdasarkan kata kunci. Status PASS atau FAIL per folder.
            </CardDescription>
          </CardHeader>
          <CardFooter className="mt-auto pt-4 border-t dark:border-gray-800">
            <Button className="w-full bg-amber-600 hover:bg-amber-700 text-white" onClick={() => navigate('/verification/coverage')}>
              Open Coverage Check
            </Button>
          </CardFooter>
        </Card>
      </div>

      {(catalogResult || searchResult || coverageResult) && (
        <Card className="mt-8 bg-gray-50 dark:bg-gray-800/50">
          <CardHeader>
            <CardTitle className="text-lg">Recent Results Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {catalogResult && (
              <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3">
                  <FileSpreadsheet className="w-5 h-5 text-blue-500" />
                  <span className="font-medium text-gray-900 dark:text-gray-100">Catalog Check</span>
                </div>
                <div className="flex gap-2">
                  <Badge variant="default" className="bg-green-600 hover:bg-green-700">{catalogResult.summary.matched} Matched</Badge>
                  <Badge variant="destructive">{catalogResult.summary.missing} Missing</Badge>
                </div>
              </div>
            )}
            {searchResult && (
              <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3">
                  <Search className="w-5 h-5 text-green-500" />
                  <span className="font-medium text-gray-900 dark:text-gray-100">Keyword Search</span>
                </div>
                <Badge variant="default">{searchResult.summary.matched_files} Files Found</Badge>
              </div>
            )}
            {coverageResult && (
              <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3">
                  <CheckSquare className="w-5 h-5 text-amber-500" />
                  <span className="font-medium text-gray-900 dark:text-gray-100">Coverage Check</span>
                </div>
                <div className="flex gap-2">
                  <Badge variant="default" className="bg-green-600 hover:bg-green-700">{coverageResult.summary.pass} Pass</Badge>
                  <Badge variant="destructive">{coverageResult.summary.fail} Fail</Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
