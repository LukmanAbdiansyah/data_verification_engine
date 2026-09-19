import React, { useState } from 'react';
import { 
  FileText, FolderOpen, Play, Download, ExternalLink, RefreshCw, 
  CheckCircle2, AlertCircle, FileSpreadsheet, Hash, Search, Clock
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Switch } from '@/components/ui/Switch';
import { Progress } from '@/components/ui/Progress';
import { Badge } from '@/components/ui/Badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { useElectron } from '@/hooks/useElectron';
import { apiService } from '@/services/api';

const WELL_CATALOG_TYPES = [
  "D.2.3 WELL_LOG_DIGITAL",
  "D.3.2 WELL_REPORT_DIGITAL",
];

const BA_TYPES = ["BADAN USAHA", "BENTUK USAHA TETAP", "UNIVERSITAS", "UNIT PELAKSANA"];
const AREA_TYPES = ["WILAYAH KERJA", "SURVEI UMUM"];
const MEDIA_TYPES = ["EKSTERNAL HARDISK", "CD-R", "DVD-R", "TAPE MAGNETIC LTO"];
const ROW_QUALITIES = ["TERVERIFIKASI OLEH SKK MIGAS", "TERVERIFIKASI OLEH DITJEN MIGAS"];

export function WellCatalogPage() {
  const { selectFolder, openInExplorer } = useElectron();

  // Selected catalog type
  const [catalogType, setCatalogType] = useState<string>("D.2.3 WELL_LOG_DIGITAL");
  const [folderPath, setFolderPath] = useState<string>("");

  // Scan state
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [folderSummary, setFolderSummary] = useState<any>(null);

  // Form states
  const [baLongName, setBaLongName] = useState<string>("");
  const [baType, setBaType] = useState<string>("BADAN USAHA");
  const [areaId, setAreaId] = useState<string>("");
  const [areaType, setAreaType] = useState<string>("WILAYAH KERJA");
  const [rowQuality, setRowQuality] = useState<string>("TERVERIFIKASI OLEH SKK MIGAS");
  const [checkedByBaId, setCheckedByBaId] = useState<string>("");
  const [mediaType, setMediaType] = useState<string>("EKSTERNAL HARDISK");
  const [generateMd5, setGenerateMd5] = useState<boolean>(false);

  // Generation state
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [progressStatus, setProgressStatus] = useState<string>("");
  const [currentFile, setCurrentFile] = useState<string>("");
  const [currentFileIndex, setCurrentFileIndex] = useState<number>(0);
  const [totalFilesCount, setTotalFilesCount] = useState<number>(0);
  const [generationResult, setGenerationResult] = useState<any>(null);
  const [tableSearch, setTableSearch] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handlePickFolder = async () => {
    try {
      const selected = await selectFolder();
      if (selected) {
        setFolderPath(selected);
        triggerScan(selected);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const triggerScan = async (path: string) => {
    if (!path) return;
    setIsScanning(true);
    setErrorMsg(null);
    try {
      const res = await apiService.scanCatalogFolder(path, "well");
      setFolderSummary(res);
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.detail || "Gagal memindai folder.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleGenerate = async () => {
    if (!folderPath) {
      setErrorMsg("Harap pilih folder data terlebih dahulu.");
      return;
    }
    setIsGenerating(true);
    setErrorMsg(null);
    setProgressPercent(15);
    setProgressStatus("Menyiapkan berkas dan memindai direktori...");

    // Smooth UI progress indicator while backend extracts metadata
    const interval = setInterval(() => {
      setProgressPercent((prev) => {
        if (prev >= 88) return prev;
        return prev + 6;
      });
    }, 500);

    try {
      const params = {
        BA_LONG_NAME: baLongName,
        BA_TYPE: baType,
        AREA_ID: areaId,
        AREA_TYPE: areaType,
        ROW_QUALITY: rowQuality,
        CHECKED_BY_BA_ID: checkedByBaId,
        MEDIA_TYPE: mediaType,
        generate_md5: generateMd5,
      };

      const res = await apiService.generateWellCatalog(catalogType, folderPath, params);

      clearInterval(interval);
      setProgressPercent(100);
      setProgressStatus("Pembuatan catalog selesai!");
      setGenerationResult(res);
    } catch (e: any) {
      clearInterval(interval);
      console.error("Well catalog generation error:", e);
      const detail = e?.response?.data?.detail;
      const msg = e?.message;
      setErrorMsg(detail || (msg ? `Gagal membuat catalog: ${msg}` : "Terjadi kesalahan saat membuat catalog well."));
    } finally {
      setIsGenerating(false);
    }
  };


  // Filtered rows for table preview
  const filteredRows = React.useMemo(() => {
    if (!generationResult?.rows) return [];
    if (!tableSearch.trim()) return generationResult.rows;
    const query = tableSearch.toLowerCase();
    return generationResult.rows.filter((row: any) =>
      Object.values(row).some((val) => String(val ?? '').toLowerCase().includes(query))
    );
  }, [generationResult, tableSearch]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4 dark:border-gray-800">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
              Well Data Catalog Generator
            </h1>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Ekstraksi metadata header log sumur LAS (D.2.3) dan laporan sumur (D.3.2) otomatis standar PPDM 3.9.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Catalog Type & Folder Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            Pilih Format Katalog & Folder Input
          </CardTitle>
          <CardDescription>
            Pilih template katalog dan folder direktori tempat file data sumur disimpan.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1.5">
                Jenis Katalog Well PPDM 3.9:
              </label>
              <select
                value={catalogType}
                onChange={(e) => setCatalogType(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                {WELL_CATALOG_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1.5">
                Folder Data Sumur:
              </label>
              <div className="flex gap-2">
                <Input
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  placeholder="C:\Data\Well\LAS_Files"
                  className="font-mono text-xs flex-1"
                />
                <Button 
                  variant="outline" 
                  onClick={handlePickFolder}
                  className="shrink-0 flex items-center gap-1.5"
                >
                  <FolderOpen className="w-4 h-4" />
                  Pilih Folder
                </Button>
              </div>
            </div>
          </div>

          {/* Folder scan preview badge */}
          {folderSummary && (
            <div className="p-3 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 text-xs flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-4">
                <span>Total File: <strong>{folderSummary.total_files}</strong></span>
                <span>File LAS (.las): <strong className="text-emerald-600 dark:text-emerald-400">{folderSummary.las_count}</strong></span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-muted-foreground">Format ditemukan:</span>
                {Object.keys(folderSummary.extension_summary || {}).map((ext) => (
                  <Badge key={ext} variant="secondary" className="text-[10px] uppercase">
                    {ext || 'no-ext'} ({folderSummary.extension_summary[ext]})
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Metadata Configuration Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Hash className="w-4 h-4 text-emerald-600" />
            Parameter Metadata Katalog
          </CardTitle>
          <CardDescription>
            Informasi administratif KKKS dan wilayah kerja sumur.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                BA_LONG_NAME (KKKS):
              </label>
              <Input
                value={baLongName}
                onChange={(e) => setBaLongName(e.target.value)}
                placeholder="e.g. PT PERTAMINA HULU ROKAN"
                className="text-xs"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                BA_TYPE:
              </label>
              <select
                value={baType}
                onChange={(e) => setBaType(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                {BA_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                AREA_ID (Blok / WK):
              </label>
              <Input
                value={areaId}
                onChange={(e) => setAreaId(e.target.value)}
                placeholder="e.g. ROKAN"
                className="text-xs"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                AREA_TYPE:
              </label>
              <select
                value={areaType}
                onChange={(e) => setAreaType(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                {AREA_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                MEDIA_TYPE:
              </label>
              <select
                value={mediaType}
                onChange={(e) => setMediaType(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                {MEDIA_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                ROW_QUALITY:
              </label>
              <select
                value={rowQuality}
                onChange={(e) => setRowQuality(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                {ROW_QUALITIES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                CHECKED_BY_BA_ID:
              </label>
              <Input
                value={checkedByBaId}
                onChange={(e) => setCheckedByBaId(e.target.value)}
                placeholder="e.g. SKK-QC-01"
                className="text-xs"
              />
            </div>
          </div>

          <div className="pt-2 border-t dark:border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Switch
                checked={generateMd5}
                onCheckedChange={setGenerateMd5}
                id="generate-well-md5-toggle"
              />
              <div>
                <label htmlFor="generate-well-md5-toggle" className="text-xs font-medium cursor-pointer">
                  Hitung MD5 Checksum Per-file
                </label>
                <p className="text-[11px] text-muted-foreground">
                  Menghitung cryptographic MD5 hash untuk kolom DECRYPT_KEY.
                </p>
              </div>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={isGenerating || !folderPath}
              className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-2"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Membuat Catalog...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Generate Catalog
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Progress display */}
      {isGenerating && (
        <Card className="border-emerald-300 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20 shadow-xs">
          <CardContent className="pt-4 pb-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <RefreshCw className="w-4 h-4 text-emerald-600 dark:text-emerald-400 animate-spin" />
                <span className="text-xs font-semibold text-gray-800 dark:text-gray-200">
                  {progressStatus}
                </span>
              </div>
              <Badge variant="secondary" className="font-mono text-xs font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-900/60 border border-emerald-200 dark:border-emerald-800">
                {progressPercent}%
              </Badge>
            </div>
            <Progress value={progressPercent} className="h-2 bg-emerald-100 dark:bg-emerald-950" />
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <Clock className="w-3.5 h-3.5 text-emerald-500 animate-pulse shrink-0" />
              <span>
                Sedang memproses {folderSummary?.total_files ? `${folderSummary.total_files} file` : 'berkas'} data sumur dan menyusun catalog Excel...
              </span>
            </div>
          </CardContent>
        </Card>
      )}


      {/* Results View */}
      {generationResult && (
        <div className="space-y-4">
          <Card className="border-green-200 dark:border-green-900 bg-green-50/20 dark:bg-green-950/20">
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
                  <CardTitle className="text-base text-green-900 dark:text-green-100">
                    Katalog Data Sumur Berhasil Dibuat
                  </CardTitle>
                </div>
                <div className="flex items-center gap-2">
                  {generationResult.output_path && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openInExplorer(generationResult.output_path)}
                        className="text-xs flex items-center gap-1.5"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        Buka di Explorer
                      </Button>
                      <a
                        href={apiService.getCatalogDownloadUrl(generationResult.output_path)}
                        download
                        target="_blank"
                        rel="noreferrer"
                      >
                        <Button size="sm" className="text-xs bg-green-600 hover:bg-green-700 text-white flex items-center gap-1.5">
                          <Download className="w-3.5 h-3.5" />
                          Unduh File Excel (.xlsx)
                        </Button>
                      </a>
                    </>
                  )}
                </div>
              </div>
              <CardDescription className="text-xs font-mono pt-1 text-gray-600 dark:text-gray-300">
                Lokasi File: {generationResult.output_path} ({generationResult.total_files} file dikatalogkan)
              </CardDescription>
            </CardHeader>
          </Card>

          {/* Table Preview */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">Pratinjau Data Katalog ({filteredRows.length} baris)</CardTitle>
                <CardDescription className="text-xs">
                  Menampilkan hasil ekstraksi parameter sumur standar PPDM 3.9.
                </CardDescription>
              </div>
              <div className="w-64">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-muted-foreground" />
                  <Input
                    placeholder="Cari sumur atau nilai..."
                    value={tableSearch}
                    onChange={(e) => setTableSearch(e.target.value)}
                    className="pl-8 text-xs h-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border overflow-x-auto max-h-[500px]">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      {generationResult.columns?.slice(0, 15).map((col: string) => (
                        <TableHead key={col} className="text-[11px] font-bold whitespace-nowrap">
                          {col}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredRows.slice(0, 100).map((row: any, i: number) => (
                      <TableRow key={i} className="hover:bg-muted/30">
                        {generationResult.columns?.slice(0, 15).map((col: string) => (
                          <TableCell key={col} className="text-xs py-2 whitespace-nowrap font-mono">
                            {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {filteredRows.length > 100 && (
                <p className="text-[11px] text-muted-foreground mt-2 text-center">
                  Menampilkan 100 dari {filteredRows.length} baris. Seluruh data tersimpan dalam file Excel.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
