import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBytes(bytes: number, decimals = 2) {
  if (!+bytes) return '0 Bytes'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

export function formatDuration(ms: number) {
  const seconds = Math.floor((ms / 1000) % 60);
  const minutes = Math.floor((ms / (1000 * 60)) % 60);
  const hours = Math.floor((ms / (1000 * 60 * 60)) % 24);

  const hoursStr = (hours < 10) ? "0" + hours : hours;
  const minutesStr = (minutes < 10) ? "0" + minutes : minutes;
  const secondsStr = (seconds < 10) ? "0" + seconds : seconds;

  if(hours > 0) return `${hoursStr}:${minutesStr}:${secondsStr}`;
  return `${minutesStr}:${secondsStr}`;
}

export function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString();
}

export function statusColor(status: string) {
  switch (status) {
    case 'PASS': return 'text-green-500';
    case 'PARTIAL': return 'text-amber-500';
    case 'MISSING': return 'text-red-500';
    case 'INVALID': return 'text-red-800';
    case 'REVIEW_REQUIRED': return 'text-orange-500';
    default: return 'text-gray-500';
  }
}

export function statusBgColor(status: string) {
  switch (status) {
    case 'PASS': return 'bg-green-500';
    case 'PARTIAL': return 'bg-amber-500';
    case 'MISSING': return 'bg-red-500';
    case 'INVALID': return 'bg-red-800';
    case 'REVIEW_REQUIRED': return 'bg-orange-500';
    default: return 'bg-gray-500';
  }
}

import { CheckCircle2, AlertCircle, XCircle, HelpCircle, AlertOctagon } from 'lucide-react';
export function statusIcon(status: string) {
  switch (status) {
    case 'PASS': return CheckCircle2;
    case 'PARTIAL': return AlertCircle;
    case 'MISSING': return XCircle;
    case 'INVALID': return AlertOctagon;
    case 'REVIEW_REQUIRED': return HelpCircle;
    default: return HelpCircle;
  }
}

export function formatApiError(err: any, fallback: string = 'An unexpected error occurred'): string {
  if (!err) return fallback;
  const detail = err?.response?.data?.detail ?? err?.detail ?? err?.message;
  if (typeof detail === 'string') {
    return detail.trim() || fallback;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: any) => {
        if (typeof item === 'string') return item;
        if (typeof item === 'object' && item !== null) {
          const loc = Array.isArray(item.loc) ? item.loc.filter((l: any) => l !== 'body').join('.') : '';
          const msg = item.msg || item.message || JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .filter(Boolean);
    return messages.length > 0 ? messages.join('; ') : fallback;
  }
  if (typeof detail === 'object' && detail !== null) {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  if (typeof err === 'string') return err;
  return fallback;
}
