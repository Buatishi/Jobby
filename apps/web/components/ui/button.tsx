import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-semibold ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98] disabled:pointer-events-none disabled:scale-100 disabled:opacity-50 data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-sm hover:-translate-y-0.5 hover:bg-primary/90 hover:shadow-md",
        primary:
          "bg-primary text-primary-foreground shadow-sm hover:-translate-y-0.5 hover:bg-primary/90 hover:shadow-md",
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:-translate-y-0.5 hover:bg-secondary/90 hover:shadow-md",
        outline:
          "border border-input bg-background shadow-sm hover:-translate-y-0.5 hover:bg-muted hover:shadow-md",
        ghost: "hover:bg-muted hover:text-foreground",
        danger:
          "bg-destructive text-destructive-foreground shadow-sm hover:-translate-y-0.5 hover:bg-destructive/90 hover:shadow-md"
      },
      size: {
        sm: "h-9 rounded-md px-3 text-xs",
        md: "h-10 px-4 py-2",
        lg: "h-12 rounded-xl px-5 text-base"
      },
      fullWidth: {
        true: "w-full",
        false: ""
      }
    },
    defaultVariants: {
      variant: "default",
      size: "md",
      fullWidth: false
    }
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className,
      disabled,
      fullWidth,
      isLoading = false,
      leftIcon,
      rightIcon,
      size,
      variant,
      asChild = false,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : "button";
    const isDisabled = disabled || isLoading;

    if (asChild) {
      return (
        <Comp
          aria-disabled={isDisabled}
          className={cn(buttonVariants({ variant, size, fullWidth, className }))}
          data-disabled={isDisabled}
          ref={ref}
          {...props}
        >
          {children}
        </Comp>
      );
    }

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, fullWidth, className }))}
        disabled={isDisabled}
        ref={ref}
        {...props}
      >
        {isLoading ? (
          <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
        ) : (
          leftIcon
        )}
        <span>{children}</span>
        {!isLoading ? rightIcon : null}
      </Comp>
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };
