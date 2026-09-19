import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Textarea } from '@/components/ui/Textarea';
import { Check, X, Info, ArrowLeft, Bot, FileText, Activity, AlertTriangle } from 'lucide-react';
import { useValidationStore } from '@/stores/validationStore';
import { apiService } from '@/services/api';
import { useLocation, useNavigate } from 'react-router-dom';
import type { RequirementResult } from '@/types';

import { useAppStore } from '@/stores/appStore';

export function ReviewPage() {
  const { results, setResults } = useValidationStore();
  const { currentRunId } = useAppStore();
  const location = useLocation();
  const navigate = useNavigate();
  const queryParams = new URLSearchParams(location.search);
  const resultId = parseInt(queryParams.get('id') || '0', 10);
  const runId = queryParams.get('run_id') || currentRunId;

  const [result, setResult] = useState<RequirementResult | null>(null);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (results.length === 0 && runId) {
      setFetching(true);
      apiService.getResults(runId)
        .then((data) => {
          setResults(data || []);
        })
        .catch((e) => console.error('Failed to load results for review:', e))
        .finally(() => setFetching(false));
    }
  }, [runId, results.length]);

  useEffect(() => {
    if (resultId && results.length > 0) {
      const found = results.find(r => r.id === resultId);
      if (found) {
        setResult(found);
        setNote(found.reviewer_note || '');
      }
    }
  }, [resultId, results]);

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center h-full space-y-4">
        {fetching ? (
          <p className="text-muted-foreground">Loading deliverable details...</p>
        ) : (
          <>
            <p className="text-muted-foreground">No result selected or result not found.</p>
            <Button variant="outline" onClick={() => navigate(runId ? `/seismic/results?run_id=${runId}` : '/seismic/results')}>
              <ArrowLeft className="w-4 h-4 mr-2"/> Back to Results
            </Button>
          </>
        )}
      </div>
    );
  }

  const handleReview = async (newStatus: string) => {
    setLoading(true);
    try {
      await apiService.submitManualReview(result.id, { new_status: newStatus, reviewer_note: note });
      // Update local store
      const updatedResults = results.map(r => 
        r.id === result.id ? { ...r, final_status: newStatus as any, reviewer_note: note } : r
      );
      setResults(updatedResults);
      navigate(runId ? `/seismic/results?run_id=${runId}` : '/seismic/results');
    } catch (e) {
      alert('Failed to submit review');
    } finally {
      setLoading(false);
    }
  };

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

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="icon" onClick={() => navigate('/seismic/results')}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <h1 className="text-3xl font-bold">Manual Review</h1>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="h-fit">
          <CardContent className="p-6 space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-lg text-primary">{result.req_id}</h3>
                {getStatusBadge(result.final_status || result.system_status)}
              </div>
              <p className="text-xl font-medium">{result.progress}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge variant="outline" className="text-xs">Format Expected: {result.format_name}</Badge>
                {result.matched_file && (
                  <Badge variant="secondary" className="text-xs"><FileText className="w-3 h-3 mr-1"/> {result.matched_file}</Badge>
                )}
                {result.evidence_level && (
                  <Badge variant="outline" className="text-xs border-amber-200 text-amber-700 bg-amber-50 dark:bg-amber-950 dark:text-amber-400">
                    <Activity className="w-3 h-3 mr-1"/> Evidence: {result.evidence_level}
                  </Badge>
                )}
              </div>
            </div>

            <div className="border-t pt-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-md flex items-center gap-2">
                  <Bot className="w-4 h-4 text-primary" /> AI Semantic Assessment
                </h3>
                {result.ai_assessment && (
                  <Badge variant="outline" className="font-mono text-xs uppercase font-semibold">
                    {result.ai_assessment.assessment.replace('_', ' ')}
                  </Badge>
                )}
              </div>
              {result.ai_assessment ? (
                <div className="space-y-3">
                  <div className="bg-primary/5 p-4 rounded-md text-sm border border-primary/10">
                    <span className="font-semibold text-xs block text-primary mb-1 uppercase tracking-wider">AI Reasoning & Rationale</span>
                    <p className="text-sm leading-relaxed">{result.ai_assessment.reasoning_summary || result.ai_assessment.assessment}</p>
                  </div>

                  {result.ai_assessment.matched_evidence && result.ai_assessment.matched_evidence.length > 0 && (
                    <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-md text-xs space-y-1">
                      <span className="font-semibold text-green-700 dark:text-green-400 block mb-1">Matched Supporting Evidence:</span>
                      <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                        {result.ai_assessment.matched_evidence.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {result.ai_assessment.missing_evidence && result.ai_assessment.missing_evidence.length > 0 && (
                    <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-md text-xs space-y-1">
                      <span className="font-semibold text-amber-700 dark:text-amber-400 block mb-1">Missing Expected Evidence:</span>
                      <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                        {result.ai_assessment.missing_evidence.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {result.ai_assessment.contradictions && result.ai_assessment.contradictions.length > 0 && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-md text-xs space-y-1">
                      <span className="font-semibold text-red-700 dark:text-red-400 block mb-1">Detected Contradictions:</span>
                      <ul className="list-disc list-inside space-y-0.5 text-red-600 dark:text-red-400">
                        {result.ai_assessment.contradictions.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-muted p-4 rounded-md text-sm italic text-muted-foreground">
                  No AI assessment generated for this item (passed technical validation or no evidence found).
                </div>
              )}
            </div>

            {result.candidates && result.candidates.length > 0 && (
              <div className="border-t pt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-md flex items-center gap-2">
                    <FileText className="w-4 h-4 text-primary" /> Matched Deliverable Files ({result.candidates.length})
                  </h3>
                  <Badge variant="outline" className="text-[11px] font-mono">
                    {result.matched_file_path || 'Repository Files'}
                  </Badge>
                </div>
                <div className="border rounded-md divide-y max-h-56 overflow-y-auto bg-card">
                  {result.candidates.map((cand, idx) => (
                    <div key={idx} className="p-2.5 flex items-center justify-between text-xs hover:bg-muted/50 transition-colors">
                      <div className="flex items-center gap-2 font-mono truncate mr-2">
                        <FileText className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                        <span className="truncate" title={cand.relative_path || cand.filename}>
                          {cand.filename}
                        </span>
                      </div>
                      <Badge variant="outline" className="text-[10px] uppercase shrink-0 font-mono">
                        {cand.evidence_level}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.evidence_details && result.evidence_details.length > 0 && (
              <div className="border-t pt-4 space-y-3">
                <h3 className="font-semibold text-md">Technical Evidence</h3>
                {result.evidence_details.map((ev, i) => (
                  <div key={i} className="bg-muted/50 p-3 rounded-md border">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold uppercase tracking-wider">{ev.evidence_type}</span>
                      <span className="text-[10px] uppercase border px-1.5 py-0.5 rounded-sm">{ev.strength}</span>
                    </div>
                    <p className="text-xs font-mono break-all whitespace-pre-wrap">{ev.content}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="h-fit sticky top-6 border-primary/20 shadow-md">
          <CardContent className="p-6 space-y-6">
            <div>
              <h3 className="font-semibold text-lg mb-2">Review Decision</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Override the system status and provide a rationale. This will be recorded in the final audit report.
              </p>
              <Textarea 
                placeholder="Enter your rationale for overriding the status (required for audit)..." 
                className="h-32 resize-none"
                value={note}
                onChange={e => setNote(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 border-t pt-6">
              <Button 
                onClick={() => handleReview('PASS')} 
                disabled={loading}
                className="bg-green-600 hover:bg-green-700 text-white w-full"
              >
                <Check className="w-4 h-4 mr-2"/> Accept PASS
              </Button>
              <Button 
                onClick={() => handleReview('PARTIAL')} 
                disabled={loading}
                variant="outline" 
                className="text-amber-600 border-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950 w-full"
              >
                <Info className="w-4 h-4 mr-2"/> Mark PARTIAL
              </Button>
              <Button 
                onClick={() => handleReview('MISSING')} 
                disabled={loading}
                variant="outline" 
                className="text-red-500 border-red-500 hover:bg-red-50 dark:hover:bg-red-950 w-full col-span-1 sm:col-span-2"
              >
                <X className="w-4 h-4 mr-2"/> Mark MISSING
              </Button>
              <Button 
                onClick={() => handleReview('INVALID')} 
                disabled={loading}
                variant="destructive" 
                className="w-full col-span-1 sm:col-span-2 bg-red-800 hover:bg-red-900"
              >
                <AlertTriangle className="w-4 h-4 mr-2" /> Mark INVALID
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
