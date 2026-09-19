import React, { useState } from 'react';
import { FolderOpen, CheckSquare, Loader2, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Switch } from '@/components/ui/Switch';
import { Badge } from '@/components/ui/Badge';
import { Textarea } from '@/components/ui/Textarea';
import { useVerificationEngineStore } from '@/stores/verificationEngineStore';
import { apiService } from '@/services/api';
import { formatApiError } from '@/lib/utils';
import { useElectron } from '@/hooks/useElectron';
import { CoverageFolderResult } from '@/types';

function FolderRow({ folder }: { folder: CoverageFolderResult }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <td className="px-4 py-3 flex items-center gap-2">
          {expanded ? <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />}
          <span className="font-medium text-gray-900 dark:text-gray-100">{folder.folder_name || '/ (Root)'}</span>
        </td>
        <td className="px-4 py-3">
          {folder.status === 'PASS' ? <Badge className="bg-green-600 hover:bg-green-700">PASS</Badge> : <Badge variant="destructive">FAIL</Badge>}
        </td>
        <td className="px-4 py-3 text-center">{folder.scanned_files}</td>
        <td className="px-4 py-3">
          <div className="flex flex-wrap gap-1">
            {folder.matched_keywords.length > 0 ? folder.matched_keywords.map((k, idx) => <Badge key={idx} variant="secondary" className="text-xs bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">{k}</Badge>) : <span className="text-xs text-gray-400">-</span>}
          </div>
        </td>
        <td className="px-4 py-3 text-red-600 dark:text-red-400 text-xs font-medium">
          {folder.missing_keywords.length > 0 ? folder.missing_keywords.join(', ') : <span className="text-gray-400 font-normal">-</span>}
        </td>
      </tr>
      {expanded && folder.matched_files.length > 0 && (
        <tr className="bg-gray-50/50 dark:bg-gray-900/20 border-b dark:border-gray-700">
          <td colSpan={5} className="px-8 py-4">
            <div className="text-xs font-semibold mb-2 text-gray-500 uppercase tracking-wider">Matched Files</div>
            <ul className="space-y-1.5">
              {folder.matched_files.map((f, i) => (
                <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-start">
                  <span className="mr-2 text-gray-400">•</span>
                  <span>
                    <span className="font-medium">{f.file_name}</span>
                    <span className="text-gray-500 ml-2 text-xs">({f.matched_keywords.join(', ')})</span>
                  </span>
                </li>
              ))}
            </ul>
          </td>
        </tr>
      )}
      {expanded && folder.matched_files.length === 0 && (
        <tr className="bg-gray-50/50 dark:bg-gray-900/20 border-b dark:border-gray-700">
          <td colSpan={5} className="px-8 py-4 text-sm text-gray-500 italic">
            No matched files in this folder.
          </td>
        </tr>
      )}
    </>
  );
}

export function CoverageCheckPage() {
  const { coverageResult, setCoverageResult, sessionId } = useVerificationEngineStore();
  const { selectFolder } = useElectron();
  
  const [folderPath, setFolderPath] = useState('');
  const [keywordsStr, setKeywordsStr] = useState('');
  const [matchMode, setMatchMode] = useState<'ANY' | 'ALL'>('ANY');
  const [recursivePerFolder, setRecursivePerFolder] = useState(false);
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBrowseFolder = async () => {
    try {
      const result = await selectFolder();
      if (result) setFolderPath(Array.isArray(result) ? result[0] : result);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCheck = async () => {
    if (!folderPath) {
      setError('Folder path harus diisi.');
      return;
    }
    const keywords = keywordsStr.split(/[\n,]+/).map(k => k.trim()).filter(k => k);
    if (keywords.length === 0) {
      setError('Keywords harus diisi minimal 1.');
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const args = {
        folder_path: folderPath,
        keywords,
        match_mode: matchMode,
        search_scope: recursivePerFolder ? 'recursive_per_folder' : 'direct_files',
        case_sensitive: caseSensitive,
      };
      const res = await apiService.runVerification('verify_keyword_coverage', args, sessionId);
      setCoverageResult(res);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><CheckSquare className="w-6 h-6 text-amber-600" /> Keyword Coverage Check</CardTitle>
          <CardDescription>Verifikasi kelengkapan dokumen per subfolder berdasarkan kata kunci</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">Target Folder Path</label>
            <div className="flex gap-2">
              <Input value={folderPath} onChange={(e) => setFolderPath(e.target.value)} placeholder="C:\path\to\target\folder" />
              <Button variant="outline" onClick={handleBrowseFolder}><FolderOpen className="w-4 h-4 mr-2" /> Browse</Button>
            </div>
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-medium flex justify-between items-center">
              <span>Keywords</span>
              <span className="text-xs text-gray-500 font-normal">Pisahkan dengan koma atau baris baru</span>
            </label>
            <Textarea value={keywordsStr} onChange={(e) => setKeywordsStr(e.target.value)} placeholder="keyword1, keyword2&#10;keyword3" rows={4} />
          </div>

          <div className="flex flex-wrap items-start gap-8 pt-2">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Match Mode</label>
              <div className="flex rounded-md shadow-sm">
                <Button 
                  type="button" 
                  variant={matchMode === 'ANY' ? 'default' : 'outline'} 
                  className={`rounded-r-none px-4 ${matchMode === 'ANY' ? 'bg-amber-600 hover:bg-amber-700 text-white' : ''}`} 
                  onClick={() => setMatchMode('ANY')}
                >
                  ANY (Salah Satu)
                </Button>
                <Button 
                  type="button" 
                  variant={matchMode === 'ALL' ? 'default' : 'outline'} 
                  className={`rounded-l-none px-4 ${matchMode === 'ALL' ? 'bg-amber-600 hover:bg-amber-700 text-white' : ''}`} 
                  onClick={() => setMatchMode('ALL')}
                >
                  ALL (Semua Wajib)
                </Button>
              </div>
              <p className="text-xs text-muted-foreground max-w-xs">
                {matchMode === 'ANY' 
                  ? '✓ PASS jika minimal ada salah satu keyword ditemukan pada subfolder.' 
                  : '⚠ PASS hanya jika seluruh keyword ditemukan pada subfolder.'}
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Search Scope</label>
              <div className="flex rounded-md shadow-sm">
                <Button type="button" variant={!recursivePerFolder ? 'default' : 'outline'} className="rounded-r-none px-4" onClick={() => setRecursivePerFolder(false)}>Direct Files Only</Button>
                <Button type="button" variant={recursivePerFolder ? 'default' : 'outline'} className="rounded-l-none px-4" onClick={() => setRecursivePerFolder(true)}>Recursive per Folder</Button>
              </div>
            </div>
            
            <div className="flex items-center space-x-2 pt-6">
              <Switch id="case-sensitive-coverage" checked={caseSensitive} onCheckedChange={setCaseSensitive} />
              <label htmlFor="case-sensitive-coverage" className="text-sm font-medium cursor-pointer">Case Sensitive</label>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-md flex items-start gap-2 mt-4 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button className="w-full mt-4 bg-amber-600 hover:bg-amber-700 text-white h-12 text-lg" onClick={handleCheck} disabled={loading}>
            {loading ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : null}
            {loading ? 'Checking Coverage...' : 'Check Coverage'}
          </Button>
        </CardContent>
      </Card>

      {coverageResult && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold">{coverageResult.summary.folders}</span>
                <span className="text-sm font-medium text-gray-500">Total Folders</span>
              </CardContent>
            </Card>
            <Card className="bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-green-600 dark:text-green-500">{coverageResult.summary.pass}</span>
                <span className="text-sm font-medium text-green-700 dark:text-green-600">Pass</span>
              </CardContent>
            </Card>
            <Card className="bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-900">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-red-600 dark:text-red-500">{coverageResult.summary.fail}</span>
                <span className="text-sm font-medium text-red-700 dark:text-red-600">Fail</span>
              </CardContent>
            </Card>
            <Card className="bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-900">
              <CardContent className="p-4 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-blue-600 dark:text-blue-500">{coverageResult.summary.scanned_files}</span>
                <span className="text-sm font-medium text-blue-700 dark:text-blue-600">Scanned Files</span>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Folder Coverage Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-800 dark:text-gray-400">
                    <tr>
                      <th className="px-4 py-3">Folder Name</th>
                      <th className="px-4 py-3 w-24">Status</th>
                      <th className="px-4 py-3 w-32 text-center">Scanned Files</th>
                      <th className="px-4 py-3 w-1/3">Matched Keywords</th>
                      <th className="px-4 py-3 w-1/4">Missing Keywords</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coverageResult.folder_results.map((r, i) => (
                      <FolderRow key={i} folder={r} />
                    ))}
                    {coverageResult.folder_results.length === 0 && (
                      <tr>
                        <td colSpan={5} className="text-center py-8 text-gray-500">
                          No folders scanned.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
