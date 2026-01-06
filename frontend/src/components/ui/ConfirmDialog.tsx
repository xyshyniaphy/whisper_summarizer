/**
 * Confirmation Dialog component
 * A reusable modal for confirming user actions
 * Use this instead of window.confirm() for better testability
 */

import { ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Modal } from './Modal'
import { Button } from './Button'

interface ConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string | ReactNode
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'danger'
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = '确定',
  cancelLabel = '取消',
  variant = 'default'
}: ConfirmDialogProps) {
  const handleConfirm = () => {
    onConfirm()
    onClose()
  }

  const isDanger = variant === 'danger'

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <div className="space-y-4">
        {/* Message with optional icon */}
        <div className="flex items-start gap-3">
          {isDanger && (
            <div className="flex-shrink-0 mt-0.5">
              <AlertTriangle className="w-5 h-5 text-red-500" data-icon="alert-triangle" />
            </div>
          )}
          <div className="flex-1">
            {typeof message === 'string' ? (
              <p className="text-gray-700 dark:text-gray-300">{message}</p>
            ) : (
              message
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex justify-end gap-3 pt-4 border-t dark:border-gray-700">
          <Button
            variant="secondary"
            onClick={onClose}
          >
            {cancelLabel}
          </Button>
          <Button
            variant={isDanger ? 'danger' : 'primary'}
            onClick={handleConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
