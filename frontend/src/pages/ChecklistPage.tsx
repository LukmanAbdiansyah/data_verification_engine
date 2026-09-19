import React, { useState, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/Dialog';
import { Textarea } from '@/components/ui/Textarea';
import { useChecklistStore } from '@/stores/checklistStore';
import { useAppStore } from '@/stores/appStore';
import { apiService } from '@/services/api';
import { formatApiError } from '@/lib/utils';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Copy, Upload, Clipboard, CheckCircle2, AlertTriangle, Loader2, RotateCcw, ArrowRight } from 'lucide-react';
import type { Requirement } from '@/types';

export function ChecklistPage() {
  const navigate = useNavigate();
  const { requirements, confirmed, addRequirement, updateRequirement, deleteRequirement, duplicateRequirement, setRequirements, setConfirmed } = useChecklistStore();
  const { currentRunId, setCurrentRunId } = useAppStore();

  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteContent, setPasteContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const safeRequirements = Array.isArray(requirements) ? requirements : [];

  const handleAdd = () => {
    const nextIdx = safeRequirements.length + 1;
    const newReq: Requirement = {
      id: Math.random().toString(36).substring(7),
      req_id: `REQ-${String(nextIdx).padStart(3, '0')}`,
      source_row: nextIdx,
      progress: 'New Deliverable Item',
      formats: ['SEG-Y'],
      validation_note: 'OK',
    };
    addRequirement(newReq);
    setConfirmed(false);
  };

  const handleClearAll = () => {
    if (confirm('Are you sure you want to clear all checklist requirements?')) {
      setRequirements([]);
      setConfirmed(false);
      setErrorMsg(null);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await apiService.uploadChecklist(file);
      if (data?.run_id) setCurrentRunId(data.run_id);

      const startIdx = safeRequirements.length;
      const rawRows = Array.isArray(data?.rows) ? data.rows : [];
      const parsedReqs: Requirement[] = rawRows.map((row: any, idx: number) => {
        const fmts = (row.format_str || 'OTHER').split(',').map((f: string) => f.trim()).filter(Boolean);
        const curIdx = startIdx + idx + 1;
        return {
          id: Math.random().toString(36).substring(7),
          req_id: `REQ-${String(curIdx).padStart(3, '0')}`,
          source_row: curIdx,
          progress: String(row.progress || 'Untitled Deliverable').trim(),
          formats: fmts.length ? fmts : ['OTHER'],
          validation_note: !row.progress ? 'Empty Progress' : 'OK',
        };
      });

      if (parsedReqs.length === 0) {
        setErrorMsg('No valid rows could be parsed from the file.');
        return;
      }

      setRequirements([...safeRequirements, ...parsedReqs]);
      setConfirmed(false);
    } catch (err: any) {
      setErrorMsg(formatApiError(err, 'Failed to parse file. Please verify format.'));
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handlePaste = async () => {
    const text = pasteContent.trim();
    if (!text) return;
    setLoading(true);
    setErrorMsg(null);

    let parsedReqs: Requirement[] = [];
    const startIdx = safeRequirements.length;

    // 1. Try backend paste parsing
    try {
      const data = await apiService.pasteChecklist(text);
      if (data?.run_id) setCurrentRunId(data.run_id);

      const rows = Array.isArray(data?.rows) ? data.rows : [];
      parsedReqs = rows.map((row: any, idx: number) => {
        const fmts = (row.format_str || 'OTHER').split(',').map((f: string) => f.trim()).filter(Boolean);
        const curIdx = startIdx + idx + 1;
        return {
          id: Math.random().toString(36).substring(7),
          req_id: `REQ-${String(curIdx).padStart(3, '0')}`,
          source_row: curIdx,
          progress: String(row.progress || 'Untitled Deliverable').trim(),
          formats: fmts.length ? fmts : ['OTHER'],
          validation_note: !row.progress ? 'Empty Progress' : 'OK',
        };
      });
    } catch (apiErr) {
      console.warn('Backend paste parser error, using client parser fallback:', apiErr);
    }

    // 2. Client-side fallback if backend returned 0 rows
    if (parsedReqs.length === 0) {
      const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
      if (lines.length > 0) {
        // Detect delimiter
        const first = lines[0];
        const delim = first.includes('\t') ? '\t' : (first.includes(';') ? ';' : ',');
        
        const hasHeader = first.toLowerCase().includes('format') || first.toLowerCase().includes('file') || first.toLowerCase().includes('progress');
        const dataLines = hasHeader ? lines.slice(1) : lines;

        dataLines.forEach((line, idx) => {
          const parts = line.split(delim).map((p) => p.trim());
          let progress = '';
          let fmt = 'OTHER';

          if (parts.length >= 3 && parts[0].match(/^\d+$/)) {
            // e.g. 1, Final Velocity PSDM, SEGY
            progress = parts[1] || '';
            fmt = parts[2] || 'OTHER';
          } else if (parts.length >= 2) {
            progress = parts[0] || '';
            fmt = parts[1] || 'OTHER';
          } else if (parts.length === 1) {
            progress = parts[0];
          }

          if (progress) {
            const fmts = fmt.split(',').map((f) => f.trim()).filter(Boolean);
            const curIdx = startIdx + idx + 1;
            parsedReqs.push({
              id: Math.random().toString(36).substring(7),
              req_id: `REQ-${String(curIdx).padStart(3, '0')}`,
              source_row: curIdx,
              progress,
              formats: fmts.length ? fmts : ['OTHER'],
              validation_note: 'OK',
            });
          }
        });
      }
    }

    setLoading(false);

    if (parsedReqs.length === 0) {
      setErrorMsg('Could not detect deliverable rows. Please ensure your text has Progress and Format columns.');
      return;
    }

    setRequirements([...safeRequirements, ...parsedReqs]);
    setConfirmed(false);
    setPasteOpen(false);
    setPasteContent('');
  };

  const handleConfirm = async () => {
    if (!currentRunId) {
      setConfirmed(true);
      return;
    }
    setLoading(true);
    try {
      await apiService.confirmChecklist(currentRunId, safeRequirements);
      setConfirmed(true);
    } catch (err: any) {
      setErrorMsg(formatApiError(err, 'Failed to save checklist to database.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Deliverable Checklist</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Authoritative source of truth. Only <strong>PROGRESS</strong> and <strong>FORMAT</strong> columns are evaluated.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            accept=".xlsx,.xls,.csv" 
            className="hidden" 
          />
          {safeRequirements.length > 0 && (
            <Button variant="ghost" onClick={handleClearAll} className="text-muted-foreground hover:text-red-500">
              <RotateCcw className="w-4 h-4 mr-2" /> Reset
            </Button>
          )}
          <Button variant="outline" onClick={() => setPasteOpen(true)} disabled={loading}>
            <Clipboard className="w-4 h-4 mr-2" /> Paste Table
          </Button>
          <Button variant="outline" onClick={() => fileInputRef.current?.click()} disabled={loading}>
            <Upload className="w-4 h-4 mr-2" /> Upload CSV/XLSX
          </Button>
          <Button onClick={handleAdd} disabled={loading}>
            <Plus className="w-4 h-4 mr-2" /> Add Row
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-md text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {confirmed && (
        <div className="p-3 bg-green-500/10 border border-green-500/20 text-green-600 dark:text-green-400 rounded-md text-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Checklist confirmed with <strong>{safeRequirements.length}</strong> requirements. Ready for repository scan & validation.</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="pass">Confirmed</Badge>
            <Button size="sm" onClick={() => navigate('/seismic/repository')} className="bg-green-600 hover:bg-green-700 text-white">
              Proceed to Repository <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          </div>
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">Req ID</TableHead>
                <TableHead>Progress (Authoritative Deliverable Name)</TableHead>
                <TableHead className="w-48">Expected Format(s)</TableHead>
                <TableHead className="w-40">Validation Note</TableHead>
                <TableHead className="w-24 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {safeRequirements.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center h-32 text-muted-foreground">
                    {loading ? (
                      <div className="flex items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>Parsing deliverable table...</span>
                      </div>
                    ) : (
                      <span>No requirements loaded. Click <strong>Upload CSV/XLSX</strong> or <strong>Paste Table</strong> to begin.</span>
                    )}
                  </TableCell>
                </TableRow>
              ) : (
                safeRequirements.map((req, idx) => {
                  const reqId = req.req_id || (req as any).no || `REQ-${String(idx + 1).padStart(3, '0')}`;
                  const progressVal = req.progress || '';
                  const formatsVal = Array.isArray(req.formats)
                    ? req.formats.join(', ')
                    : typeof req.formats === 'string'
                    ? req.formats
                    : (req as any).format || 'OTHER';
                  const note = req.validation_note || (req as any).validationNote || 'OK';
                  const badgeVariant =
                    note === 'OK'
                      ? 'outline'
                      : String(note).includes('Duplicate')
                      ? 'review'
                      : 'destructive';

                  return (
                    <TableRow key={req.id || idx}>
                      <TableCell className="font-mono text-xs font-semibold text-muted-foreground">
                        {reqId}
                      </TableCell>
                      <TableCell>
                        <Input
                          value={progressVal}
                          onChange={(e) => {
                            updateRequirement(req.id, { progress: e.target.value });
                            setConfirmed(false);
                          }}
                          className="h-8 text-sm"
                          placeholder="e.g. Final Pre-STM stack"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          value={formatsVal}
                          onChange={(e) => {
                            const list = e.target.value.split(',').map((f) => f.trim()).filter(Boolean);
                            updateRequirement(req.id, { formats: list });
                            setConfirmed(false);
                          }}
                          className="h-8 text-sm"
                          placeholder="e.g. SEG-Y or ASCII, SEG-Y"
                        />
                      </TableCell>
                      <TableCell>
                        <Badge variant={badgeVariant} className="text-xs">
                          {note}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right space-x-1">
                        <Button variant="ghost" size="icon" onClick={() => duplicateRequirement(req.id)} title="Duplicate requirement">
                          <Copy className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="text-red-500 hover:text-red-600" onClick={() => deleteRequirement(req.id)} title="Delete requirement">
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between pt-2">
        <span className="text-sm text-muted-foreground">
          Total: <strong>{safeRequirements.length}</strong> requirements
        </span>
        <div className="flex items-center gap-3">
          <Button size="lg" onClick={handleConfirm} disabled={safeRequirements.length === 0 || loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
            Confirm Checklist
          </Button>
          {confirmed && (
            <Button size="lg" onClick={() => navigate('/seismic/repository')} className="bg-green-600 hover:bg-green-700 text-white">
              Next: Repository <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          )}
        </div>
      </div>

      <Dialog open={pasteOpen} onOpenChange={setPasteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Paste Deliverable Table Data</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Paste CSV or spreadsheet rows (tab, comma, or semicolon separated). Columns like <strong>Progress / File / Deliverable</strong> and <strong>Format</strong> are auto-detected.
          </p>
          {errorMsg && (
            <div className="p-2.5 bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded text-xs flex items-center gap-1.5 mt-2">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
          <Textarea
            placeholder={"No.,File,Format\n1,Final Velocity PSDM,SEGY\n2,Final PSDM Gather,SEGY\n3,Final Processing Report,PDF"}
            className="h-64 mt-2 font-mono text-xs"
            value={pasteContent}
            onChange={(e) => setPasteContent(e.target.value)}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setPasteOpen(false)}>Cancel</Button>
            <Button onClick={handlePaste} disabled={!pasteContent.trim() || loading}>
              {loading ? 'Processing...' : 'Import Rows'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
