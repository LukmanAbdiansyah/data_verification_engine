import * as React from "react"
import { cn } from "@/lib/utils"

export function Tabs({ defaultValue, onValueChange, value, children, className }: { defaultValue?: string, value?: string, onValueChange?: (val: string) => void, children: React.ReactNode, className?: string }) {
  const [active, setActive] = React.useState(value || defaultValue);
  
  React.useEffect(() => {
    if (value !== undefined) setActive(value);
  }, [value]);

  const contextValue = React.useMemo(() => ({
    active, setActive: (val: string) => {
      setActive(val);
      if (onValueChange) onValueChange(val);
    }
  }), [active, onValueChange]);

  return (
    <TabsContext.Provider value={contextValue}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

const TabsContext = React.createContext<{active: string | undefined, setActive: (val: string) => void}>({ active: undefined, setActive: () => {} });

export function TabsList({ children, className }: { children: React.ReactNode, className?: string }) {
  return <div className={cn("inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground", className)}>{children}</div>
}

export function TabsTrigger({ value, children, className }: { value: string, children: React.ReactNode, className?: string }) {
  const { active, setActive } = React.useContext(TabsContext);
  const isActive = active === value;
  return (
    <button
      onClick={() => setActive(value)}
      className={cn("inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50", 
        isActive ? "bg-background text-foreground shadow" : "", className)}
    >
      {children}
    </button>
  )
}

export function TabsContent({ value, children, className }: { value: string, children: React.ReactNode, className?: string }) {
  const { active } = React.useContext(TabsContext);
  if (active !== value) return null;
  return <div className={cn("mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2", className)}>{children}</div>
}
