import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`rounded-xl border bg-white shadow-card ${className}`} {...props} />;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "green" | "amber" | "red" }) {
  const tones = {
    neutral: "bg-neutral-100 text-neutral-700",
    green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
    red: "bg-red-50 text-red-700 ring-red-600/20",
  };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${tones[tone]}`}>{children}</span>;
}

export function Button({ className = "", variant = "primary", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" }) {
  const variants = {
    primary: "bg-neutral-900 text-white hover:bg-neutral-700",
    secondary: "border bg-white text-neutral-800 hover:bg-neutral-50",
    ghost: "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
  };
  return <button className={`inline-flex h-9 items-center justify-center rounded-lg px-3.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`} {...props} />;
}

export function Dialog({ open, onOpenChange, trigger, title, description, children }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  trigger: ReactNode;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/30" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-white p-6 shadow-xl focus:outline-none">
          <DialogPrimitive.Title className="text-lg font-semibold">{title}</DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-1.5 text-sm leading-6 text-neutral-500">{description}</DialogPrimitive.Description>
          {children}
          <DialogPrimitive.Close className="absolute right-4 top-4 grid size-8 place-items-center rounded-md text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700" aria-label="Close">
            <X className="size-4" />
          </DialogPrimitive.Close>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
