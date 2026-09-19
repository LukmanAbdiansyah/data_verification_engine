import React, { useState } from 'react';
import { FileSpreadsheet, FolderOpen, Loader2, AlertCircle, Plus, X, Trash2, CheckCircle2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Switch } from '@/components/ui/Switch';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { useVerificationEngineStore } from '@/stores/verificationEngineStore';
import { apiService } from '@/services/api';
import { formatApiError } from '@/lib/utils';
import { useElectron } from '@/hooks/useElectron';

export function CatalogCheckPage() {
  const { catalogResult, setCatalogResult, sessionId } = useVerificationEngineStore();
  const { selectFiles, selectFolder } = useElectron();
  
  const [metadataPaths, setMetadataPaths] = useState<string[]>([]);
  const [manualInputPath, setManualInputPath] = useState('');
  const [folderPath, setFolderPath] = useState('');
  const [sheetName, setSheetName] = useState('0');
  const [columnName, setColumnName] = useState('ORIGINAL_FILE_NAME');
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBrowseMetadata = async () => {
    try {
      const results = await selectFiles({ filters: [{ name: 'Excel Files', extensions: ['xlsx', 'xls'] }] });
      if (results && results.length > 0) {
        setMetadataPaths((prev) => {
          const combined = [...prev];
          for (const p of results) {
            if (!combined.includes(p)) combined.push(p);
          }
          return combined;
        });
        setError(null);
      }
    } catch (e) {
      console.error('File browse error:', e);
    }
  };

  const handleAddManualPath = () => {
    const trimmed = manualInputPath.trim();
    if (!trimmed) return;
    const paths = trimmed.split(/[\n,]+/).map((p) => p.trim()).filter((p) => p);
    setMetadataPaths((prev) => {
      const combined = [...prev];
      for (const p of paths) {
        if (!combined.includes(p)) combined.push(p);
      }
      return combined;
    });
    setManualInputPath('');
    setError(null);
  };

  const handleRemoveMetadataPath = (indexToRemove: number) => {
    setMetadataPaths((prev) => prev.filter((_, idx) => idx !== indexToRemove));
  };

  const handleClearAllMetadata = () => {
    setMetadataPaths([]);
  };

  const handleBrowseFolder = async () => {
    try {
      const result = await selectFolder();
      if (result) {
        setFolderPath(Array.isArray(result) ? result[0] : result);
        setError(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleRun = async () => {
    const allPaths = [...metadataPaths];
    if (manualInputPath.trim()) {
      const paths = manualInputPath.split(/[\n,]+/).map((p) => p.trim()).filter((p) => p);
      for (const p of paths) {
        if (!allPaths.includes(p)) allPaths.push(p);
      }
    }

    if (allPaths.length === 0) {
      setError('Pilih atau masukkan minimal satu file metadata Excel.');
      return;
    }

    if (!folderPath.trim()) {
      setError('Path folder target harus diisi.');
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const args = {
        metadata_paths: allPaths,
        folder_path: folderPath.trim(),
        sheet_name: sheetName,
        file_column: columnName,
        case_sensitive: caseSensitive,
      };
      const res = await apiService.runVerification('verify_catalog', args, sessionId);
      setCatalogResult(res);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'MATCHED': return <Badge className="bg-green-600 hover:bg-green-700">MATCHED</Badge>;
      case 'MISSING': return <Badge variant="destructive">MISSING</Badge>;
      case 'DUPLICATE': return <Badge className="bg-amber-500 hover:bg-amber-600 text-white">DUPLICATE</Badge>;
      case 'EMPTY': return <Badge variant="secondary">EMPTY</Badge>;
      default: return <Badge>{status}</Badge>;
    }
  };

  const getFileNameFromPath = (fullPath: string) => {
    return fullPath.replace(/\\/g, '/').split('/').pop() || fullPath;
  };

  const hasMultipleCatalogs = (catalogResult?.summary?.catalog_files_count || 0) > 1 || metadataPaths.length > 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2">
            <FileSpreadsheet className="w-6 h-6 text-blue-600" /> Multi-Catalog Verification
          </CardTitle>
          <CardDescription>
            Validasi metadata Excel (bisa lebih dari satu file) terhadap file fisik di folder target. Jika file terdapat di salah satu catalog, maka statusnya <strong>MATCHED</strong>.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Metadata selection section */}
          <div className="space-y-3 p-4 border rounded-lg bg-muted/20">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <label className="text-sm font-semibold flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4 text-blue-600" />
                <span>Metadata Excel Catalogs ({metadataPaths.length} file dipilih)</span>
              </label>
              <div className="flex items-center gap-2">
                {metadataPaths.length > 0 && (
                  <Button variant="ghost" size="sm" onClick={handleClearAllMetadata} className="text-xs text-red-500 hover:text-red-600 h-8">
                    <Trash2 className="w-3.5 h-3.5 mr-1" /> Clear All
                  </Button>
                )}
                <Button variant="outline" size="sm" onClick={handleBrowseMetadata} className="h-8">
                  <Plus className="w-3.5 h-3.5 mr-1" /> Browse File(s)
                </Button>
              </div>
            </div>

            {/* Input for manual path or pasting */}
            <div className="flex gap-2">
              <Input 
                value={manualInputPath} 
                onChange={(e) => setManualInputPath(e.target.value)} 
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddManualPath(); } }}
                placeholder="Ketik atau tempel path file Excel lalu klik Tambah..." 
                className="text-sm font-mono"
              />
              <Button variant="secondary" onClick={handleAddManualPath} disabled={!manualInputPath.trim()} className="shrink-0">
                Tambah
              </Button>
            </div>

            {/* List of selected metadata files */}
            {metadataPaths.length > 0 ? (
              <div className="space-y-2 mt-2 pt-2 border-t">
                {metadataPaths.map((p, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded bg-background border text-xs font-mono">
                    <div className="flex items-center gap-2 truncate pr-2" title={p}>
                      <Badge variant="outline" className="text-[10px] shrink-0">#{idx + 1}</Badge>
                      <span className="font-semibold text-foreground shrink-0">{getFileNameFromPath(p)}</span>
                      <span className="text-muted-foreground truncate hidden md:inline">({p})</span>
                    </div>
                    <button 
                      onClick={() => handleRemoveMetadataPath(idx)} 
                      className="p-1 text-muted-foreground hover:text-red-500 rounded hover:bg-muted"
                      title="Hapus file ini"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                Belum ada file catalog dipilih. Klik <strong>Browse File(s)</strong> (bisa pilih banyak file sekaligus) atau ketik path di atas.
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2 md:col-span-1">
              <label className="text-sm font-medium">Target Folder Path</label>
              <div className="flex gap-2">
                <Input value={folderPath} onChange={(e) => setFolderPath(e.target.value)} placeholder="C:\path\to\target\folder" />
                <Button variant="outline" onClick={handleBrowseFolder}><FolderOpen className="w-4 h-4 mr-2" /> Browse</Button>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Sheet Name / Index</label>
              <Input value={sheetName} onChange={(e) => setSheetName(e.target.value)} placeholder="0 or Sheet1" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">File Column Name</label>
              <Input value={columnName} onChange={(e) => setColumnName(e.target.value)} placeholder="ORIGINAL_FILE_NAME" />
            </div>
          </div>
          
          <div className="flex items-center space-x-2 pt-1">
            <Switch id="case-sensitive-catalog" checked={caseSensitive} onCheckedChange={setCaseSensitive} />
            <label htmlFor="case-sensitive-catalog" className="text-sm font-medium leading-none cursor-pointer">
              Case Sensitive
            </label>
          </div>

          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-md flex items-start gap-2 mt-4 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button className="w-full mt-4 bg-green-600 hover:bg-green-700 text-white h-12 text-lg" onClick={handleRun} disabled={loading}>
            {loading ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : null}
            {loading ? 'Running Verification...' : 'Run Verification'}
          </Button>
        </CardContent>
      </Card>

      {catalogResult && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card className="bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-green-600 dark:text-green-500">{catalogResult.summary.matched}</span>
                <span className="text-sm font-medium text-green-700 dark:text-green-600">Matched</span>
              </CardContent>
            </Card>
            <Card className="bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-900">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-red-600 dark:text-red-500">{catalogResult.summary.missing}</span>
                <span className="text-sm font-medium text-red-700 dark:text-red-600">Missing</span>
              </CardContent>
            </Card>
            <Card className="bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-900">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-amber-600 dark:text-amber-500">{catalogResult.summary.duplicate}</span>
                <span className="text-sm font-medium text-amber-700 dark:text-amber-600">Duplicate</span>
              </CardContent>
            </Card>
            <Card className="bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-900">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-blue-600 dark:text-blue-500">{catalogResult.summary.extra}</span>
                <span className="text-sm font-medium text-blue-700 dark:text-blue-600">Extra Files</span>
              </CardContent>
            </Card>
            <Card className="bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-gray-700 dark:text-gray-300">{catalogResult.summary.empty}</span>
                <span className="text-sm font-medium text-gray-500">Empty Rows</span>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle>Results</CardTitle>
                <CardDescription className="mt-1">
                  Total {catalogResult.summary.catalog_rows} baris metadata dari {catalogResult.summary.catalog_files_count || 1} file catalog diverifikasi terhadap {catalogResult.summary.scanned_files} file fisik di folder.
                </CardDescription>
              </div>
              {hasMultipleCatalogs && (
                <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-900/20 dark:text-blue-300">
                  {catalogResult.summary.catalog_files_count || metadataPaths.length} Catalogs Evaluated
                </Badge>
              )}
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="all">
                <TabsList className="mb-4 flex flex-wrap gap-2 h-auto p-1">
                  <TabsTrigger value="all">All ({catalogResult.catalog_results.length})</TabsTrigger>
                  <TabsTrigger value="matched">Matched ({catalogResult.summary.matched})</TabsTrigger>
                  <TabsTrigger value="missing">Missing ({catalogResult.summary.missing})</TabsTrigger>
                  <TabsTrigger value="duplicate">Duplicate ({catalogResult.summary.duplicate})</TabsTrigger>
                  <TabsTrigger value="extra">Extra ({catalogResult.extra_files.length})</TabsTrigger>
                </TabsList>

                {['all', 'matched', 'missing', 'duplicate'].map((tab) => (
                  <TabsContent key={tab} value={tab} className="overflow-x-auto m-0 outline-none">
                    <table className="w-full text-sm text-left">
                      <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-800 dark:text-gray-400">
                        <tr>
                          {hasMultipleCatalogs && <th className="px-4 py-3 whitespace-nowrap">Catalog File</th>}
                          <th className="px-4 py-3 whitespace-nowrap">Row #</th>
                          <th className="px-4 py-3">File Name</th>
                          <th className="px-4 py-3 whitespace-nowrap">Status</th>
                          <th className="px-4 py-3 whitespace-nowrap text-center">Found Count</th>
                          <th className="px-4 py-3">Paths</th>
                        </tr>
                      </thead>
                      <tbody>
                        {catalogResult.catalog_results
                          .filter(r => tab === 'all' || r.status.toLowerCase() === tab)
                          .map((r, i) => (
                            <tr key={i} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                              {hasMultipleCatalogs && (
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <Badge variant="outline" className="text-[11px] font-mono">
                                    {r.catalog_file || '-'}
                                  </Badge>
                                </td>
                              )}
                              <td className="px-4 py-3">{r.row_number}</td>
                              <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{r.file_name}</td>
                              <td className="px-4 py-3">{getStatusBadge(r.status)}</td>
                              <td className="px-4 py-3 text-center">{r.file_count}</td>
                              <td className="px-4 py-3">
                                {r.found_paths.length > 0 ? (
                                  <div className="max-h-24 overflow-y-auto space-y-1 pr-2">
                                    {r.found_paths.map((p, idx) => (
                                      <div key={idx} className="text-xs text-gray-500 break-all">{p}</div>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-xs text-gray-400 italic">-</span>
                                )}
                              </td>
                            </tr>
                        ))}
                        {catalogResult.catalog_results.filter(r => tab === 'all' || r.status.toLowerCase() === tab).length === 0 && (
                          <tr>
                            <td colSpan={hasMultipleCatalogs ? 6 : 5} className="text-center py-8 text-gray-500">No {tab !== 'all' ? tab : ''} results found.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </TabsContent>
                ))}

                <TabsContent value="extra" className="overflow-x-auto m-0 outline-none">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-800 dark:text-gray-400">
                      <tr>
                        <th className="px-4 py-3">File Name</th>
                        <th className="px-4 py-3">Relative Path</th>
                      </tr>
                    </thead>
                    <tbody>
                      {catalogResult.extra_files.map((r, i) => (
                        <tr key={i} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                          <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{r.file_name}</td>
                          <td className="px-4 py-3 text-gray-500 break-all">{r.relative_path}</td>
                        </tr>
                      ))}
                      {catalogResult.extra_files.length === 0 && (
                        <tr>
                          <td colSpan={2} className="text-center py-8 text-gray-500">No extra files found.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
