import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Progress } from '@/components/ui/Progress';
import { useElectron } from '@/hooks/useElectron';
import { useAppStore } from '@/stores/appStore';
import { useValidationStore } from '@/stores/validationStore';
import { apiService } from '@/services/api';
import { formatApiError } from '@/lib/utils';
import { useWebSocket } from '@/hooks/useWebSocket';
import { FolderSearch, FolderOpen, CheckCircle2, AlertTriangle, Loader2, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function RepositoryPage() {
  const { selectFolder, isElectron } = useElectron();
  const { currentRunId, setCurrentRunId } = useAppStore();
  const { scanProgress, isScanning, setIsScanning, setScanProgress } = useValidationStore();
  const [repoPath, setRepoPath] = useState('');
  const [isBrowsing, setIsBrowsing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const navigate = useNavigate();

  // Connect to websocket if we have a run ID
  useWebSocket(currentRunId);

  React.useEffect(() => {
    if (currentRunId) {
      apiService.getScanStatus(currentRunId).then((res) => {
        if (res && res.status === 'completed' && res.files_scanned > 0) {
          setScanProgress({
            files_scanned: res.files_scanned,
            folders_scanned: res.folders_scanned || 0,
            current_folder: '',
            elapsed_seconds: res.elapsed_seconds || 0,
            file_type_counts: res.file_type_counts || {},
            status: 'completed',
          });
        }
      }).catch(() => {});
    }
  }, [currentRunId]);

  const handleSelect = async () => {
    setIsBrowsing(true);
    setErrorMsg(null);
    try {
      const path = await selectFolder();
      if (path) {
        setRepoPath(path);
      }
    } catch (err: any) {
      console.error('Browse error:', err);
      setErrorMsg('Failed to open folder picker. You can also paste or type the path directly.');
    } finally {
      setIsBrowsing(false);
    }
  };

  const handleScan = async () => {
    if (!repoPath.trim()) {
      setErrorMsg('Please enter or browse to a repository folder path.');
      return;
    }
    setIsScanning(true);
    setErrorMsg(null);
    setScanProgress(null);
    try {
      const resp = await apiService.scanRepository(repoPath.trim(), currentRunId || undefined);
      if (resp.run_id) setCurrentRunId(resp.run_id);
      setScanProgress({
        files_scanned: resp.files_scanned || 0,
        folders_scanned: resp.folders_scanned || 0,
        current_folder: '',
        elapsed_seconds: resp.elapsed_seconds || 0,
        file_type_counts: resp.file_type_counts || {},
        status: resp.status || 'completed',
      });
    } catch (err: any) {
      setErrorMsg(formatApiError(err, 'Failed to scan repository. Please verify the folder path exists.'));
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold">Repository Configuration</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Select the root folder containing the seismic deliverable data files to scan and verify.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Deliverable Workspace</CardTitle>
          <CardDescription>
            Choose a local drive, network share, or NAS folder containing deliverables
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              placeholder="e.g. C:\SeismicData\Block_A or \\nas\seismic\2026_delivery"
              className="flex-1 font-mono text-sm"
              disabled={isScanning || isBrowsing}
            />
            <Button
              variant="outline"
              onClick={handleSelect}
              disabled={isScanning || isBrowsing}
              className="shrink-0"
            >
              {isBrowsing ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <FolderOpen className="w-4 h-4 mr-2" />
              )}
              {isBrowsing ? 'Opening Dialog...' : 'Browse Folder'}
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            {isElectron
              ? 'Running in Desktop mode (native Windows Explorer picker enabled).'
              : 'Running in Web mode: clicking Browse will open a Windows folder dialog via backend, or you can paste the full folder path directly.'}
          </p>

          <Button
            className="w-full"
            size="lg"
            disabled={!repoPath.trim() || isScanning || isBrowsing}
            onClick={handleScan}
          >
            {isScanning ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <FolderSearch className="w-4 h-4 mr-2" />
            )}
            {isScanning ? 'Scanning Directory...' : 'Scan Repository'}
          </Button>

          {errorMsg && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-md text-sm flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {scanProgress && (
            <div className="space-y-4 mt-6 p-5 border rounded-md bg-muted/20">
              <div className="flex justify-between items-center text-sm font-semibold">
                <span className="flex items-center gap-2">
                  {scanProgress.status === 'completed' ? (
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                  ) : (
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                  )}
                  {scanProgress.status === 'completed' ? 'Repository Scan Completed' : 'Scanning repository...'}
                </span>
                <span className="font-mono text-xs bg-background px-2.5 py-1 rounded border">
                  {scanProgress.files_scanned} files found
                </span>
              </div>

              {scanProgress.status !== 'completed' && (
                <Progress value={100} className="h-2 animate-pulse" />
              )}

              {scanProgress.current_folder && (
                <div className="text-xs text-muted-foreground font-mono truncate">
                  Scanning: {scanProgress.current_folder}
                </div>
              )}

              {scanProgress.status === 'completed' && (
                <div className="pt-4 border-t space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-semibold">File Type Distribution:</span>
                    <span className="text-xs text-muted-foreground font-mono">
                      Completed in {scanProgress.elapsed_seconds.toFixed(2)}s ({scanProgress.folders_scanned} folders)
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {Object.entries(scanProgress.file_type_counts || {}).map(([ext, count]) => (
                      <div
                        key={ext}
                        className="bg-background border px-3 py-1.5 flex justify-between items-center rounded text-xs"
                      >
                        <span className="font-mono text-muted-foreground uppercase">{ext || 'no-ext'}</span>
                        <span className="font-bold text-foreground">{count as number}</span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-6 pt-2 flex justify-end">
                    <Button
                      onClick={() => navigate('/seismic/validation')}
                      className="bg-green-600 hover:bg-green-700 text-white"
                      size="lg"
                    >
                      Proceed to Validation <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
