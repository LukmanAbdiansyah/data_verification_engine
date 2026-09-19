import * as React from "react"
import { cn } from "@/lib/utils"

export interface SwitchProps extends React.InputHTMLAttributes<HTMLInputElement> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, checked, onCheckedChange, ...props }, ref) => {
    return (
      <div 
        className={cn("peer inline-flex h-[20px] w-[36px] shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50", 
          checked ? "bg-primary" : "bg-input", className)}
        onClick={() => onCheckedChange?.(!checked)}
      >
        <span
          className={cn("pointer-events-none block h-4 w-4 rounded-full bg-background shadow-lg ring-0 transition-transform", 
            checked ? "translate-x-4" : "translate-x-0")}
        />
        <input type="checkbox" className="hidden" checked={checked} readOnly ref={ref} {...props} />
      </div>
    )
  }
)
Switch.displayName = "Switch"
export { Switch }
