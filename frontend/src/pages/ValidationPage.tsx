import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Progress } from '@/components/ui/Progress';
import { useAppStore } from '@/stores/appStore';
import { useValidationStore } from '@/stores/validationStore';
import { apiService } from '@/services/api';
import { formatApiError } from '@/lib/utils';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Play, Square, Loader2, CheckCircle2, AlertTriangle, ArrowRight, RotateCcw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function ValidationPage() {
  const { currentRunId } = useAppStore();
  const { validationProgress, isValidating, setIsValidating, setResults, setValidationProgress } = useValidationStore();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [statusText, setStatusText] = useState('Ready to start');
  const navigate = useNavigate();
  const pollTimerRef = useRef<any>(null);

  // Connect to websocket to receive progress updates in real time
  useWebSocket(currentRunId);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  const handleStart = async () => {
    if (!currentRunId) {
      setErrorMsg('No active validation run. Please make sure you have loaded requirements in Checklist and scanned the Repository first.');
      return;
    }

    setIsValidating(true);
    setErrorMsg(null);
    setStatusText('Starting validation pipeline...');

    try {
      await apiService.runValidation(currentRunId);

      // Start fallback status polling in case WebSocket is blocked or offline
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      pollTimerRef.current = setInterval(async () => {
        try {
          const statusRes = await apiService.getValidationStatus(currentRunId);
          if (statusRes.status === 'completed') {
            clearInterval(pollTimerRef.current);
            setIsValidating(false);
            const resultsRes = await apiService.getResults(currentRunId);
            setResults(resultsRes || []);
            setValidationProgress({
              stage: 'Completed',
              processed: resultsRes.length,
              total: resultsRes.length,
              message: `Validation finished with ${resultsRes.length} evaluated deliverables.`,
              status: 'completed',
              run_id: currentRunId,
            });
          } else if (statusRes.status === 'failed') {
            clearInterval(pollTimerRef.current);
            setIsValidating(false);
            setErrorMsg('Validation pipeline reported an error.');
          }
        } catch (e) {
          // ignore transient polling errors
        }
      }, 1500);

    } catch (err: any) {
      setIsValidating(false);
      setErrorMsg(formatApiError(err, 'Validation failed to start. Please verify Checklist and Repository.'));
    }
  };

  const handleCancel = async () => {
    if (!currentRunId) return;
    try {
      await apiService.cancelValidation(currentRunId);
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      setIsValidating(false);
      setStatusText('Validation cancelled.');
    } catch (e) {}
  };

  const handleReset = () => {
    setValidationProgress(null);
    setErrorMsg(null);
    setStatusText('Ready to start');
  };

  const percent = validationProgress && validationProgress.total > 0
    ? Math.round((validationProgress.processed / validationProgress.total) * 100)
    : isValidating
    ? 25
    : 0;

  const isCompleted = validationProgress?.status === 'completed';

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold">Validation Runner</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Execute rule-first deterministic verification and AI semantic evaluation.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Pipeline Execution</CardTitle>
          <CardDescription>
            Matches deliverable items with repository files, SEG-Y headers, and AI semantic assessment
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <Button
              size="lg"
              className="flex-1 bg-green-600 hover:bg-green-700 text-white disabled:bg-muted disabled:text-muted-foreground"
              onClick={handleStart}
              disabled={isValidating || isCompleted}
            >
              {isValidating ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              {isValidating ? 'Validating Pipeline...' : isCompleted ? 'Validation Completed' : 'Start Validation'}
            </Button>

            {isCompleted ? (
              <Button size="lg" variant="outline" onClick={handleReset}>
                <RotateCcw className="w-4 h-4 mr-2" /> Re-run Validation
              </Button>
            ) : (
              <Button
                size="lg"
                variant="destructive"
                className="w-full sm:w-40"
                disabled={!isValidating}
                onClick={handleCancel}
              >
                <Square className="w-4 h-4 mr-2" /> Cancel
              </Button>
            )}
          </div>

          {errorMsg && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-md text-sm flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold block">Validation Pre-Check</span>
                <span>{errorMsg}</span>
              </div>
            </div>
          )}

          <div className="space-y-4 p-6 border rounded-md bg-muted/20">
            <div className="flex justify-between items-center mb-1">
              <h3 className="font-semibold text-sm">
                {validationProgress?.stage || (isValidating ? 'Processing...' : statusText)}
              </h3>
              {(validationProgress || isValidating) && (
                <span className="text-xs font-mono font-bold bg-background px-2 py-0.5 rounded border">
                  {percent}%
                </span>
              )}
            </div>

            <Progress value={percent} className="h-3" />

            <div className="text-xs text-center text-muted-foreground font-mono truncate">
              {validationProgress?.message || (isValidating ? 'Evaluating candidate files against deliverables...' : 'Click "Start Validation" to begin')}
            </div>

            {isCompleted && (
              <div className="mt-6 pt-6 border-t flex flex-col items-center justify-center space-y-4">
                <div className="flex items-center text-green-600 gap-2">
                  <CheckCircle2 className="w-6 h-6" />
                  <span className="font-bold text-lg">Validation Completed Successfully!</span>
                </div>
                <Button size="lg" onClick={() => navigate('/seismic/results')} className="bg-primary hover:bg-primary/90 text-primary-foreground">
                  View Results Table <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
