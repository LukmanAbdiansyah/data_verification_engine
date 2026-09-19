import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Button } from '@/components/ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { useValidationStore } from '@/stores/validationStore';
import { useAppStore } from '@/stores/appStore';
import { apiService } from '@/services/api';
import { Download, Search, AlertCircle, FileText, ChevronRight, Loader2, ArrowLeft, RefreshCw } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { Status, RequirementResult } from '@/types';

export function ResultsPage() {
  const { results, setResults } = useValidationStore();
  const { currentRunId, setCurrentRunId } = useAppStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const queryRunId = searchParams.get('run_id');
  const activeRunId = queryRunId || currentRunId;

  const [filterStatus, setFilterStatus] = useState<Status | 'ALL'>('ALL');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeRunId) {
      if (queryRunId && queryRunId !== currentRunId) {
        setCurrentRunId(queryRunId);
      }
      loadResults(activeRunId);
    }
  }, [queryRunId]);

  const loadResults = async (runId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getResults(runId);
      setResults(data || []);
    } catch (e: any) {
      console.error('Failed to load results:', e);
      setError('Gagal memuat hasil validasi untuk sesi ini.');
    } finally {
      setLoading(false);
    }
  };

  const filteredResults = results.filter((r) => {
    const matchesStatus = filterStatus === 'ALL' || (r.final_status || r.system_status) === filterStatus;
    const searchLower = search.toLowerCase();
    const matchesSearch = 
      r.progress.toLowerCase().includes(searchLower) || 
      r.req_id.toLowerCase().includes(searchLower) ||
      (r.matched_file || '').toLowerCase().includes(searchLower);
    
    return matchesStatus && matchesSearch;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASS': return <Badge variant="pass">PASS</Badge>;
      case 'PARTIAL': return <Badge variant="partial">PARTIAL</Badge>;
      case 'MISSING': return <Badge variant="destructive">MISSING</Badge>;
      case 'INVALID': return <Badge variant="destructive" className="bg-red-800">INVALID</Badge>;
      case 'REVIEW_REQUIRED': return <Badge variant="review">REVIEW REQUIRED</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  const counts = {
    ALL: results.length,
    PASS: results.filter(r => (r.final_status || r.system_status) === 'PASS').length,
    PARTIAL: results.filter(r => (r.final_status || r.system_status) === 'PARTIAL').length,
    MISSING: results.filter(r => (r.final_status || r.system_status) === 'MISSING').length,
    INVALID: results.filter(r => (r.final_status || r.system_status) === 'INVALID').length,
    REVIEW_REQUIRED: results.filter(r => (r.final_status || r.system_status) === 'REVIEW_REQUIRED').length,
  };

  const handleExport = async () => {
    if (!activeRunId) return;
    try {
      const blob = await apiService.exportReport(activeRunId, 'xlsx');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Seismic_Report_${activeRunId.substring(0, 8)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export failed', e);
      alert('Failed to export report');
    }
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {queryRunId && (
            <Button variant="ghost" size="sm" onClick={() => navigate('/seismic/history')}>
              <ArrowLeft className="w-4 h-4 mr-1" /> History
            </Button>
          )}
          <div>
            <h1 className="text-3xl font-bold">Validation Results</h1>
            {activeRunId && (
              <p className="text-xs text-muted-foreground font-mono mt-1">
                Run ID: <span className="font-semibold text-primary">{activeRunId}</span>
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {activeRunId && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => loadResults(activeRunId)} 
              disabled={loading}
              title="Refresh results"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          )}
          <Button variant="outline" onClick={handleExport} disabled={!activeRunId || results.length === 0 || loading}>
            <Download className="w-4 h-4 mr-2" /> Export XLSX Report
          </Button>
        </div>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardContent className="p-4 flex flex-col flex-1 h-full space-y-4">
          <div className="flex flex-col md:flex-row items-center gap-4">
            <div className="relative w-full md:w-64 shrink-0">
              <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
              <Input 
                placeholder="Search deliverables..." 
                className="pl-9" 
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <Tabs value={filterStatus} onValueChange={(v) => setFilterStatus(v as any)} className="w-full overflow-x-auto">
              <TabsList className="inline-flex w-max">
                <TabsTrigger value="ALL">All ({counts.ALL})</TabsTrigger>
                <TabsTrigger value="PASS">Pass ({counts.PASS})</TabsTrigger>
                <TabsTrigger value="PARTIAL">Partial ({counts.PARTIAL})</TabsTrigger>
                <TabsTrigger value="MISSING">Missing ({counts.MISSING})</TabsTrigger>
                <TabsTrigger value="INVALID">Invalid ({counts.INVALID})</TabsTrigger>
                <TabsTrigger value="REVIEW_REQUIRED">Review ({counts.REVIEW_REQUIRED})</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
          
          <div className="flex-1 overflow-auto border rounded-md relative">
            <Table>
              <TableHeader className="sticky top-0 bg-card z-10 shadow-sm">
                <TableRow>
                  <TableHead className="w-24">Req ID</TableHead>
                  <TableHead>Deliverable Progress</TableHead>
                  <TableHead className="w-32">Format</TableHead>
                  <TableHead className="w-64">Matched File</TableHead>
                  <TableHead className="w-32 text-center">Status</TableHead>
                  <TableHead className="w-24 text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-16">
                      <div className="flex flex-col justify-center items-center gap-2 text-muted-foreground">
                        <Loader2 className="w-6 h-6 animate-spin text-primary" />
                        <span>Memuat hasil validasi...</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : error ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-destructive">
                      <div className="flex justify-center items-center gap-2">
                        <AlertCircle className="w-5 h-5 shrink-0" />
                        <span>{error}</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : results.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                      No results available. Run a validation first or select a run from History.
                    </TableCell>
                  </TableRow>
                ) : filteredResults.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                      No items match your filters.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredResults.map((row) => {
                    const status = row.final_status || row.system_status;
                    return (
                      <TableRow key={row.id} className="group hover:bg-muted/50 transition-colors">
                        <TableCell className="font-mono text-xs">{row.req_id}</TableCell>
                        <TableCell className="font-medium">{row.progress}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-[10px] uppercase">{row.format_name}</Badge>
                        </TableCell>
                        <TableCell>
                          {row.matched_file ? (
                            <div className="flex items-center gap-2 text-xs font-mono truncate max-w-[200px]" title={row.matched_file}>
                              <FileText className="w-3 h-3 text-muted-foreground shrink-0" />
                              <span className="truncate">{row.matched_file}</span>
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-xs italic">Not found</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {getStatusBadge(status)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={() => navigate(`/seismic/review?id=${row.id}${activeRunId ? `&run_id=${activeRunId}` : ''}`)}
                            className="text-xs h-7 px-2.5 hover:bg-accent"
                          >
                            Details <ChevronRight className="w-3.5 h-3.5 ml-1" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
