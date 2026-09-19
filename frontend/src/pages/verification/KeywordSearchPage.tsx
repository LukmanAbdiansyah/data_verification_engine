import React, { useState } from 'react';
import { FolderOpen, Search, Loader2, AlertCircle } from 'lucide-react';
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

export function KeywordSearchPage() {
  const { searchResult, setSearchResult, sessionId } = useVerificationEngineStore();
  const { selectFolder } = useElectron();
  
  const [folderPath, setFolderPath] = useState('');
  const [keywordsStr, setKeywordsStr] = useState('');
  const [matchMode, setMatchMode] = useState<'ANY' | 'ALL'>('ANY');
  const [recursive, setRecursive] = useState(true);
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

  const handleSearch = async () => {
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
        case_sensitive: caseSensitive,
        recursive,
      };
      const res = await apiService.runVerification('search_files_by_keywords', args, sessionId);
      setSearchResult(res);
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
          <CardTitle className="text-2xl flex items-center gap-2"><Search className="w-6 h-6 text-green-600" /> Keyword File Search</CardTitle>
          <CardDescription>Cari file berdasarkan kata kunci pada nama file</CardDescription>
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

          <div className="flex flex-wrap items-center gap-8 pt-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Match Mode</label>
              <div className="flex rounded-md shadow-sm">
                <Button type="button" variant={matchMode === 'ANY' ? 'default' : 'outline'} className="rounded-r-none px-6" onClick={() => setMatchMode('ANY')}>ANY</Button>
                <Button type="button" variant={matchMode === 'ALL' ? 'default' : 'outline'} className="rounded-l-none px-6" onClick={() => setMatchMode('ALL')}>ALL</Button>
              </div>
            </div>
            
            <div className="flex items-center space-x-2 pt-6">
              <Switch id="recursive-search" checked={recursive} onCheckedChange={setRecursive} />
              <label htmlFor="recursive-search" className="text-sm font-medium cursor-pointer">Recursive</label>
            </div>
            
            <div className="flex items-center space-x-2 pt-6">
              <Switch id="case-sensitive-search" checked={caseSensitive} onCheckedChange={setCaseSensitive} />
              <label htmlFor="case-sensitive-search" className="text-sm font-medium cursor-pointer">Case Sensitive</label>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-md flex items-start gap-2 mt-4 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button className="w-full mt-4 h-12 text-lg bg-green-600 hover:bg-green-700 text-white" onClick={handleSearch} disabled={loading}>
            {loading ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : null}
            {loading ? 'Searching...' : 'Search Files'}
          </Button>
        </CardContent>
      </Card>

      {searchResult && (
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
            <CardDescription className="text-base">
              Found <strong className="text-gray-900 dark:text-gray-100">{searchResult.summary.matched_files}</strong> files matching <strong className="text-gray-900 dark:text-gray-100">{searchResult.matched_keywords.length}</strong> keywords out of {searchResult.summary.scanned_files} scanned files.
            </CardDescription>
            {searchResult.matched_keywords.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3">
                <span className="text-sm text-gray-500 mr-2 self-center">Matched keywords:</span>
                {searchResult.matched_keywords.map((k, i) => (
                  <Badge key={i} className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 hover:bg-green-200">{k}</Badge>
                ))}
              </div>
            )}
          </CardHeader>
          <CardContent>
            {searchResult.matched_files.length === 0 ? (
              <div className="text-center py-12 text-gray-500 border border-dashed rounded-lg dark:border-gray-700">
                <Search className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
                <p>No files found matching the given keywords.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-800 dark:text-gray-400">
                    <tr>
                      <th className="px-4 py-3">File Name</th>
                      <th className="px-4 py-3">Relative Path</th>
                      <th className="px-4 py-3">Matched Keywords</th>
                    </tr>
                  </thead>
                  <tbody>
                    {searchResult.matched_files.map((r, i) => (
                      <tr key={i} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{r.file_name}</td>
                        <td className="px-4 py-3 text-gray-500 break-all">{r.relative_path}</td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {r.matched_keywords.map((k, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs">{k}</Badge>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
