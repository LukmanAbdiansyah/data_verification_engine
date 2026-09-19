import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Progress } from '@/components/ui/Progress';
import { useValidationStore } from '@/stores/validationStore';
import { useChecklistStore } from '@/stores/checklistStore';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, AlertCircle, XCircle, AlertOctagon, HelpCircle } from 'lucide-react';

export function DashboardPage() {
  const navigate = useNavigate();
  const { results } = useValidationStore();
  const { requirements } = useChecklistStore();

  const counts = {
    PASS: results.filter(r => (r.final_status || r.system_status) === 'PASS').length,
    PARTIAL: results.filter(r => (r.final_status || r.system_status) === 'PARTIAL').length,
    MISSING: results.filter(r => (r.final_status || r.system_status) === 'MISSING').length,
    INVALID: results.filter(r => (r.final_status || r.system_status) === 'INVALID').length,
    REVIEW_REQUIRED: results.filter(r => (r.final_status || r.system_status) === 'REVIEW_REQUIRED').length,
  };

  const total = results.length;
  const completion = total === 0 ? 0 : Math.round((counts.PASS / total) * 100);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="flex gap-2">
          <Button onClick={() => navigate('/seismic/checklist')} variant="outline">Edit Checklist</Button>
          <Button onClick={() => navigate('/seismic/validation')}>New Validation</Button>
        </div>
      </div>

      {total === 0 ? (
        <Card className="flex flex-col items-center justify-center p-12 text-center">
          <HelpCircle size={48} className="text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold mb-2">No active validation data</h2>
          <p className="text-muted-foreground mb-6">Start by configuring your checklist and selecting a repository.</p>
          <Button onClick={() => navigate('/seismic/checklist')}>Get Started</Button>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Overall Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4 mb-2">
                <div className="text-4xl font-bold">{completion}%</div>
                <div className="flex-1">
                  <Progress value={completion} className="h-3" />
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                {counts.PASS} of {total} requirements fully validated
              </p>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <Card className="bg-green-500/10 border-green-500/20">
              <CardContent className="p-4 flex flex-col items-center">
                <CheckCircle2 size={24} className="text-green-500 mb-2" />
                <div className="text-3xl font-bold text-green-700 dark:text-green-400">{counts.PASS}</div>
                <div className="text-xs font-semibold uppercase tracking-wider text-green-600 dark:text-green-500">Pass</div>
              </CardContent>
            </Card>

            <Card className="bg-amber-500/10 border-amber-500/20">
              <CardContent className="p-4 flex flex-col items-center">
                <AlertCircle size={24} className="text-amber-500 mb-2" />
                <div className="text-3xl font-bold text-amber-700 dark:text-amber-400">{counts.PARTIAL}</div>
                <div className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-500">Partial</div>
              </CardContent>
            </Card>

            <Card className="bg-red-500/10 border-red-500/20">
              <CardContent className="p-4 flex flex-col items-center">
                <XCircle size={24} className="text-red-500 mb-2" />
                <div className="text-3xl font-bold text-red-700 dark:text-red-400">{counts.MISSING}</div>
                <div className="text-xs font-semibold uppercase tracking-wider text-red-600 dark:text-red-500">Missing</div>
              </CardContent>
            </Card>

            <Card className="bg-red-800/10 border-red-800/20">
              <CardContent className="p-4 flex flex-col items-center">
                <AlertOctagon size={24} className="text-red-800 dark:text-red-500 mb-2" />
                <div className="text-3xl font-bold text-red-900 dark:text-red-400">{counts.INVALID}</div>
                <div className="text-xs font-semibold uppercase tracking-wider text-red-800 dark:text-red-500">Invalid</div>
              </CardContent>
            </Card>

            <Card className="bg-orange-500/10 border-orange-500/20">
              <CardContent className="p-4 flex flex-col items-center">
                <HelpCircle size={24} className="text-orange-500 mb-2" />
                <div className="text-3xl font-bold text-orange-700 dark:text-orange-400">{counts.REVIEW_REQUIRED}</div>
                <div className="text-xs font-semibold uppercase tracking-wider text-orange-600 dark:text-orange-500">Review</div>
              </CardContent>
            </Card>
          </div>
          
          <div className="flex justify-center mt-6">
             <Button size="lg" onClick={() => navigate('/seismic/results')}>View Detailed Results</Button>
          </div>
        </>
      )}
    </div>
  );
}
