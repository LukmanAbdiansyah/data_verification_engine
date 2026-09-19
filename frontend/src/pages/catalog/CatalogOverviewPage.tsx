import { useNavigate } from 'react-router-dom';
import { Waves, FileText, CheckCircle2, ArrowRight, ShieldCheck, Database, FolderOpen, FileSpreadsheet, Play, Fingerprint } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import seismicVolume from '@/assets/seismic-volume.svg';
import wellLog from '@/assets/well-log.svg';
import energyLandscape from '@/assets/hero-energy-landscape.svg';
import contourWaves from '@/assets/contour-waves.svg';

const generators = [
  {
    id: 'seismic', icon: Waves, title: 'Seismic Data Catalog Generator', count: 6, image: seismicVolume,
    description: 'Ekstraksi otomatis header SEG-Y (2D & 3D), Line Name dari Textual Header EBCDIC/ASCII, SP / CDP min-max, Sample Interval, Record Length, Inline/Crossline, serta Checksum MD5.',
    formats: [
      { code: 'B.1.5.1', label: 'SEIS 2D FIELD' }, { code: 'B.1.5.2', label: 'SEIS 2D PROCESS' },
      { code: 'B.2.3.1', label: 'SEIS 3D FIELD' }, { code: 'B.2.3.2', label: 'SEIS 3D PROCESS' },
      { code: 'B.1.6.1', label: 'SEIS 2D NAVI' }, { code: 'B.2.4.1', label: 'SEIS 3D NAVI' },
    ],
  },
  {
    id: 'well', icon: FileText, title: 'Well Data Catalog Generator', count: 2, image: wellLog,
    description: 'Ekstraksi metadata file LAS log sumur (Well Name, Field, Date, Top/Base Depth, Logging Company, Log Curves Title) dan pengkatalogan file laporan sumur (Well Reports).',
    formats: [
      { code: 'D.2.3', label: 'WELL_LOG_DIGITAL', detail: 'Ekstraksi parameter sumur otomatis dari header file log LAS (.las).' },
      { code: 'D.3.2', label: 'WELL_REPORT_DIGITAL', detail: 'Pengkatalogan laporan teknis sumur (PDF, DOCX, TXT, dsb).' },
    ],
  },
];
const capabilities = [
  { icon: FolderOpen, title: 'Pemindaian Rekursif', detail: 'Folder lokal & network NAS' },
  { icon: Database, title: 'Standar PPDM 3.9', detail: 'Struktur metadata terstandar' },
  { icon: Fingerprint, title: 'Checksum MD5', detail: 'Verifikasi integritas data' },
  { icon: FileSpreadsheet, title: 'Excel Export', detail: 'Output katalog .xlsx' },
];
const features = [
  { icon: FolderOpen, color: 'blue', title: 'Pemindaian Folder Rekursif', detail: 'Menjelajahi subfolder lokal atau network NAS secara mendalam dan mendeteksi seluruh deliverable.' },
  { icon: ShieldCheck, color: 'purple', title: 'Checksum MD5 Terintegrasi', detail: 'Menghitung hash MD5 per file untuk pemeriksaan integritas data dan verifikasi arsip migas.' },
  { icon: FileSpreadsheet, color: 'orange', title: 'Ekspor Standar Excel PPDM 3.9', detail: 'Menghasilkan lembar kerja Excel (.xlsx) dengan nama kolom dan struktur katalog PPDM 3.9.' },
];

export function CatalogOverviewPage() {
  const navigate = useNavigate();
  return (
    <div className="catalog-workspace mx-auto w-full max-w-[1600px] space-y-4">
      <section className="catalog-header relative isolate overflow-hidden" aria-labelledby="catalog-title">
        <img src={energyLandscape} alt="" aria-hidden="true" className="catalog-landscape pointer-events-none absolute" />
        <img src={contourWaves} alt="" aria-hidden="true" className="catalog-contours pointer-events-none absolute" />
        <div className="relative z-10">
          <span className="catalog-badge">PPDM 3.9</span>
          <h1 id="catalog-title" className="mt-2 text-[32px] font-bold leading-tight tracking-tight">Catalog <span className="text-[var(--dv-blue)]">Generator</span></h1>
          <p className="mt-2 max-w-[620px] text-sm text-muted-foreground">Pembuatan katalog metadata data teknis migas otomatis berstandar PPDM 3.9.</p>
        </div>
      </section>
      <div className="catalog-capabilities grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 rounded-lg border bg-card" aria-label="Kemampuan katalog">
        {capabilities.map(({ icon: Icon, title, detail }) => (
          <div key={title} className="flex items-center gap-3 px-4 py-3">
            <Icon size={19} className="shrink-0 text-[var(--dv-blue)]" aria-hidden="true" />
            <div><p className="text-xs font-semibold">{title}</p><p className="mt-0.5 text-[11px] text-muted-foreground">{detail}</p></div>
          </div>
        ))}
      </div>
      <div className="catalog-generators grid gap-4 min-[1100px]:grid-cols-2">
        {generators.map(({ id, icon: Icon, title, count, image, description, formats }) => (
          <section key={id} className={`generator-panel generator-${id} flex min-w-0 flex-col`} aria-labelledby={`${id}-title`}>
            <header className="flex items-center gap-3">
              <div className="generator-icon"><Icon size={24} aria-hidden="true" /></div>
              <div className="min-w-0"><p className="generator-eyebrow">{id.toUpperCase()} DATA</p><h2 id={`${id}-title`} className="generator-title">{title}</h2></div>
            </header>
            <div className="generator-description">
              <div><span className="catalog-badge">{count} Format PPDM 3.9</span><p>{description}</p></div>
              <img src={image} alt="" aria-hidden="true" className="generator-illustration pointer-events-none" />
            </div>
            <div className="mt-auto">
              <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">Format katalog yang didukung</h3>
              <ul className={`grid gap-2 ${id === 'seismic' ? 'catalog-format-grid grid-cols-1 md:grid-cols-2 min-[1100px]:grid-cols-1 min-[1280px]:grid-cols-2' : ''}`}>
                {formats.map(format => (
                  <li key={format.code} className="catalog-format-row"><CheckCircle2 size={16} aria-hidden="true" /><div><p className="font-mono"><strong>{format.code}</strong> {format.label}</p>{'detail' in format && <p className="mt-1 text-xs text-muted-foreground">{format.detail}</p>}</div></li>
                ))}
              </ul>
            </div>
            <Button className={`generator-launch mt-4 h-10 max-md:h-auto w-full gap-2 whitespace-normal rounded-lg text-[13px] font-semibold text-white shadow-none ${id === 'seismic' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-emerald-600 hover:bg-emerald-700'}`} onClick={() => navigate(`/catalog/${id}`)}><Play size={15} className="shrink-0" aria-hidden="true" /><span>Buka {id === 'seismic' ? 'Seismic' : 'Well'} Catalog Generator</span><ArrowRight size={16} className="shrink-0" aria-hidden="true" /></Button>
          </section>
        ))}
      </div>
      <section className="grid gap-3 min-[1100px]:grid-cols-3" aria-label="Fitur teknis">
        {features.map(({ icon: Icon, color, title, detail }) => (
          <div key={title} className="flex items-start gap-3 rounded-lg border bg-card p-4">
            <div className={`feature-icon feature-${color}`}><Icon size={21} aria-hidden="true" /></div>
            <div><h3 className="text-[13px] font-semibold">{title}</h3><p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{detail}</p></div>
          </div>
        ))}
      </section>
      <footer className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t pt-3 text-[11px] text-muted-foreground"><span className="font-medium">Data Verificator</span><span>Technical Data Catalog</span><span className="ml-auto font-mono">PPDM 3.9</span></footer>
    </div>
  );
}
