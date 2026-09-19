import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { apiService } from '@/services/api';
import { useAppStore } from '@/stores/appStore';
import { useValidationStore } from '@/stores/validationStore';
import { useNavigate } from 'react-router-dom';
import { ExternalLink, Loader2, Trash2, RefreshCw } from 'lucide-react';
import type { RunSummary } from '@/types';

export function HistoryPage() {
  const [history, setHistory] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);
  const { currentRunId, setCurrentRunId } = useAppStore();
  const { reset: resetValidation } = useValidationStore();
  const navigate = useNavigate();

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await apiService.getHistory();
      setHistory(data || []);
    } catch (e) {
      console.error('Failed to load history', e);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenRun = (runId: string) => {
    setCurrentRunId(runId);
    navigate(`/seismic/results?run_id=${runId}`);
  };

  const handleDeleteRun = async (runId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const confirmed = window.confirm(
      `Hapus sesi validasi (${runId.substring(0, 8)})? Data analisis untuk sesi ini akan dihapus.`
    );
    if (!confirmed) return;

    setDeletingId(runId);
    try {
      await apiService.deleteRun(runId);
      setHistory((prev) => prev.filter((r) => r.run_id !== runId));
      if (currentRunId === runId) {
        setCurrentRunId(null);
        resetValidation();
      }
    } catch (err) {
      console.error('Failed to delete run:', err);
      alert('Gagal menghapus riwayat validasi.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearAll = async () => {
    const confirmed = window.confirm(
      'Apakah Anda yakin ingin menghapus SEMUA riwayat validasi? Tindakan ini akan menghapus seluruh data validasi dan tidak dapat dibatalkan.'
    );
    if (!confirmed) return;

    setClearing(true);
    try {
      await apiService.clearAllHistory();
      setHistory([]);
      setCurrentRunId(null);
      resetValidation();
    } catch (err) {
      console.error('Failed to clear all history:', err);
      alert('Gagal membersihkan seluruh riwayat validasi.');
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Validation History</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {history.length} sesi validasi tersimpan
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadHistory}
            disabled={loading || clearing}
            title="Muat ulang riwayat"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleClearAll}
            disabled={loading || clearing || history.length === 0}
            title="Hapus seluruh riwayat validasi"
          >
            {clearing ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4 mr-2" />
            )}
            Clear All History
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run ID / Date</TableHead>
                <TableHead>Repository</TableHead>
                <TableHead>Checklist</TableHead>
                <TableHead>Results Summary</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-12">
                    <div className="flex justify-center items-center gap-2 text-muted-foreground">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Loading history...
                    </div>
                  </TableCell>
                </TableRow>
              ) : history.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-12 text-muted-foreground">
                    Tidak ada riwayat validasi. Silakan jalankan validasi baru.
                  </TableCell>
                </TableRow>
              ) : (
                history.map((run) => (
                  <TableRow key={run.run_id} className="hover:bg-muted/40 transition-colors">
                    <TableCell>
                      <div className="font-mono text-xs font-semibold">{run.run_id.substring(0, 8)}</div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(run.date).toLocaleString()}
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-xs" title={run.repository || 'N/A'}>
                      {run.repository || 'N/A'}
                    </TableCell>
                    <TableCell className="text-sm">{run.checklist || 'Pasted/Uploaded'}</TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        <Badge variant="outline" className="text-[10px]">T: {run.total}</Badge>
                        <Badge variant="pass" className="text-[10px]">P: {run.pass_count}</Badge>
                        {(run.partial_count > 0 || run.missing_count > 0 || run.invalid_count > 0) && (
                          <Badge variant="destructive" className="text-[10px]">
                            E: {run.missing_count + run.invalid_count}
                          </Badge>
                        )}
                        {run.review_count > 0 && (
                          <Badge variant="review" className="text-[10px]">R: {run.review_count}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleOpenRun(run.run_id)}
                          title="Buka hasil validasi sesi ini"
                        >
                          <ExternalLink className="w-4 h-4 mr-1 text-primary" /> Open
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => handleDeleteRun(run.run_id, e)}
                          disabled={deletingId === run.run_id}
                          className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                          title="Hapus sesi ini"
                        >
                          {deletingId === run.run_id ? (
                            <Loader2 className="w-4 h-4 animate-spin text-destructive" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
