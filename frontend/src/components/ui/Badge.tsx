/**
 * Badge component with Tailwind CSS
 */

import { HTMLAttributes, forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../utils/cn'

const badgeVariants = cva(
  'px-2 py-1 text-xs font-medium rounded-full',
  {
    variants: {
      variant: {
        success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
        warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        gray: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
      },
    },
    defaultVariants: {
      variant: 'info',
    },
  }
)

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(badgeVariants({ variant }), className)}
        {...props}
      />
    )
  }
)

Badge.displayName = 'Badge'
