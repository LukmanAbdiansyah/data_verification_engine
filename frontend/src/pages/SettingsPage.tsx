import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Switch } from '@/components/ui/Switch';
import { apiService } from '@/services/api';
import { formatApiError } from '@/lib/utils';
import { Save, Activity, CheckCircle2, AlertTriangle, Loader2, Eye, EyeOff, Sparkles } from 'lucide-react';
import type { Settings } from '@/types';

export function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    theme: 'system',
    cache_enabled: true,
    segy_validation_enabled: true,
    ai_enabled: true,
    unsloth_base_url: 'http://100.x.x.x:8000/v1',
    api_key: '',
    model_name: 'Qwen/Qwen2.5-Coder-32B-Instruct',
    timeout: 120,
    max_tokens: 1000,
    temperature: 0,
    max_concurrent_requests: 2,
  });

  const [initialLoading, setInitialLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    latency?: number;
    available_models?: string[];
  } | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setInitialLoading(true);
    try {
      const data = await apiService.getSettings();
      if (data) {
        setSettings((prev) => ({
          ...prev,
          ...data,
          unsloth_base_url: data.unsloth_base_url || prev.unsloth_base_url,
          model_name: data.model_name || prev.model_name,
        }));
      }
    } catch (e) {
      console.error('Failed to load settings from server', e);
    } finally {
      setInitialLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveSuccess(false);
    try {
      await apiService.updateSettings(settings);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e: any) {
      alert(formatApiError(e, 'Failed to save settings'));
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await apiService.testConnection(settings);
      const isOk = Boolean(res.connected && (res.model_ok || (res.available_models && res.available_models.length > 0)));

      if (res.available_models && res.available_models.length > 0) {
        setAvailableModels(res.available_models);
        // If current model is blank, pick first available model
        if (!settings.model_name) {
          setSettings((prev) => ({ ...prev, model_name: res.available_models![0] }));
        }
      }

      setTestResult({
        success: isOk,
        message: res.error
          ? res.error
          : res.available_models && res.available_models.length > 0
          ? `Connected successfully! Detected ${res.available_models.length} model(s) on server.`
          : res.model_ok
          ? 'Connected successfully! Model responded to verification prompt.'
          : 'Server reachable, but model check failed.',
        latency: res.latency_ms,
        available_models: res.available_models || [],
      });
    } catch (e: any) {
      setTestResult({
        success: false,
        message: formatApiError(e, 'Connection failed'),
      });
    } finally {
      setIsTesting(false);
    }
  };

  if (initialLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-muted-foreground gap-2">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>Loading settings...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto pb-10">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure application parameters, format parsers, and AI inference connectivity.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>General Preferences</CardTitle>
          <CardDescription>File caching and technical inspection options</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Enable Validation Cache</div>
              <div className="text-sm text-muted-foreground">Speed up repeated scans by checking file mtime/size</div>
            </div>
            <Switch
              checked={settings.cache_enabled}
              onCheckedChange={(c) => setSettings({ ...settings, cache_enabled: c })}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Enable SEG-Y Deep Parsing</div>
              <div className="text-sm text-muted-foreground">
                Inspect 3200-byte EBCDIC/ASCII textual header and 400-byte binary header
              </div>
            </div>
            <Switch
              checked={settings.segy_validation_enabled}
              onCheckedChange={(c) => setSettings({ ...settings, segy_validation_enabled: c })}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Semantic Verification (Unsloth via Tailscale)</CardTitle>
          <CardDescription>
            Configure the private LLM inference server for semantic requirement matching
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex items-center justify-between border-b pb-4">
            <div>
              <div className="font-medium">Enable AI Semantic Verification</div>
              <div className="text-sm text-muted-foreground">
                Allow AI to analyze ambiguous evidence and detect migration contradictions
              </div>
            </div>
            <Switch
              checked={settings.ai_enabled}
              onCheckedChange={(c) => setSettings({ ...settings, ai_enabled: c })}
            />
          </div>

          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Unsloth Base URL (Tailscale)</label>
              <Input
                value={settings.unsloth_base_url}
                onChange={(e) => setSettings({ ...settings, unsloth_base_url: e.target.value })}
                placeholder="http://100.x.x.x:8000/v1"
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Example: <code>http://100.x.x.x:8000/v1</code> or <code>http://myserver.ts.net:8000/v1</code>
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">API Key</label>
              <div className="relative">
                <Input
                  type={showApiKey ? 'text' : 'password'}
                  value={settings.api_key}
                  onChange={(e) => setSettings({ ...settings, api_key: e.target.value })}
                  placeholder="Optional — leave blank if unauthenticated"
                  className="font-mono text-sm pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                >
                  {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Model Name</label>
                {availableModels.length > 0 && (
                  <span className="text-xs text-green-600 dark:text-green-400 font-medium flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5" />
                    {availableModels.length} model(s) detected from server
                  </span>
                )}
              </div>

              {availableModels.length > 0 ? (
                <div className="space-y-2">
                  <select
                    value={settings.model_name}
                    onChange={(e) => setSettings({ ...settings, model_name: e.target.value })}
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring font-mono"
                  >
                    <option value="" disabled>-- Select a detected model --</option>
                    {availableModels.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground whitespace-nowrap">Or custom input:</span>
                    <Input
                      value={settings.model_name}
                      onChange={(e) => setSettings({ ...settings, model_name: e.target.value })}
                      placeholder="Custom model name"
                      className="h-8 font-mono text-xs flex-1"
                    />
                  </div>
                </div>
              ) : (
                <Input
                  value={settings.model_name}
                  onChange={(e) => setSettings({ ...settings, model_name: e.target.value })}
                  placeholder="e.g. Qwen/Qwen2.5-Coder-32B-Instruct"
                  className="font-mono text-sm"
                />
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="space-y-2">
                <label className="text-sm font-medium">Timeout (seconds)</label>
                <Input
                  type="number"
                  value={settings.timeout}
                  onChange={(e) => setSettings({ ...settings, timeout: parseInt(e.target.value) || 120 })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Max Concurrent Requests</label>
                <Input
                  type="number"
                  value={settings.max_concurrent_requests}
                  onChange={(e) =>
                    setSettings({ ...settings, max_concurrent_requests: parseInt(e.target.value) || 2 })
                  }
                />
              </div>
            </div>
          </div>

          {/* Test connection result banner */}
          {testResult && (
            <div
              className={`p-4 border rounded-md text-sm flex flex-col gap-2.5 transition-all ${
                testResult.success
                  ? 'bg-green-500/10 border-green-500/30 text-green-700 dark:text-green-300'
                  : 'bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-semibold">
                  {testResult.success ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0" />
                  )}
                  <span>{testResult.success ? 'Connection Successful' : 'Connection Failed'}</span>
                </div>
                {testResult.latency !== undefined && testResult.latency > 0 && (
                  <span className="text-xs font-mono bg-background/50 px-2 py-0.5 rounded border">
                    Latency: {testResult.latency} ms
                  </span>
                )}
              </div>
              <p className="text-xs font-mono break-all whitespace-pre-wrap">{testResult.message}</p>

              {testResult.available_models && testResult.available_models.length > 0 && (
                <div className="mt-1 pt-2.5 border-t border-green-500/20">
                  <span className="text-xs font-semibold block mb-1.5">
                    Select a model from server ({testResult.available_models.length}):
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {testResult.available_models.map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setSettings((prev) => ({ ...prev, model_name: m }))}
                        className={`text-xs px-2.5 py-1 rounded border font-mono transition-colors ${
                          settings.model_name === m
                            ? 'bg-green-600 text-white border-green-600 font-bold shadow-sm'
                            : 'bg-background/80 hover:bg-background border-green-500/30 text-green-800 dark:text-green-200'
                        }`}
                        title="Click to select this model"
                      >
                        {m} {settings.model_name === m ? '✓' : ''}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {saveSuccess && (
            <div className="p-3 bg-green-500/10 border border-green-500/30 text-green-700 dark:text-green-400 rounded-md text-sm flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>Settings saved successfully!</span>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-between bg-muted/20 border-t p-4">
          <Button
            variant="outline"
            onClick={handleTestConnection}
            disabled={isTesting}
          >
            {isTesting ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Activity className="w-4 h-4 mr-2" />
            )}
            {isTesting ? 'Testing Connection...' : 'Test Connection'}
          </Button>

          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            Save Settings
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
