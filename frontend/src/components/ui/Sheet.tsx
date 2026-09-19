import * as React from "react"
import { cn } from "@/lib/utils"

export function Sheet({ open, onOpenChange, children }: { open: boolean, onOpenChange: (open: boolean) => void, children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="fixed inset-0 bg-black/50 transition-opacity" onClick={() => onOpenChange(false)} />
      <div className="z-50 w-full max-w-sm sm:max-w-md bg-background h-full shadow-lg flex flex-col transform transition-transform animate-in slide-in-from-right-full">
        {children}
      </div>
    </div>
  )
}

export function SheetContent({ children, className }: { children: React.ReactNode, className?: string }) {
  return <div className={cn("p-6 overflow-y-auto flex-1", className)}>{children}</div>
}

export function SheetHeader({ children, className }: { children: React.ReactNode, className?: string }) {
  return <div className={cn("flex flex-col space-y-2 text-center sm:text-left p-6 border-b", className)}>{children}</div>
}

export function SheetTitle({ children, className }: { children: React.ReactNode, className?: string }) {
  return <h2 className={cn("text-lg font-semibold text-foreground", className)}>{children}</h2>
}
