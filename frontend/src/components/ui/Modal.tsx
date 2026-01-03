/**
 * Modal component with Tailwind CSS
 */

import { ReactNode, useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '../../utils/cn'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  className?: string
}

export function Modal({ isOpen, onClose, title, children, className }: ModalProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  // Use conditional return instead of early return to avoid hooks violation
  return isOpen ? (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className={cn(
        "relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto",
        className
      )}>
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between p-6 border-b dark:border-gray-700">
            <h2 className="text-xl font-semibold">{title}</h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Content */}
        <div className={cn("p-6", !title && "pt-6")}>
          {children}
        </div>
      </div>
    </div>
  ) : null
}
