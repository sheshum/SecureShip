import { useEffect } from 'react'

interface ToastProps {
  message: string
  type?: 'success' | 'error' | 'info'
  onClose: () => void
  duration?: number
}

export function Toast({ message, type = 'success', onClose, duration = 3000 }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, duration)
    return () => clearTimeout(timer)
  }, [duration, onClose])

  const bgColors = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500'
  }

  return (
    <div className="pointer-events-none fixed inset-0 z-50 flex items-start justify-center px-4 py-6 sm:items-start sm:justify-end sm:p-6">
      <div 
        className={`pointer-events-auto flex w-full max-w-sm overflow-hidden rounded-lg shadow-lg ${bgColors[type]} animate-in slide-in-from-top-5 fade-in duration-300`}
        role="alert"
      >
        <div className="flex w-full items-center justify-between p-4">
          <p className="text-sm font-medium text-white">{message}</p>
          <button
            onClick={onClose}
            className="ml-4 inline-flex flex-shrink-0 rounded-md text-white hover:opacity-75 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2"
            aria-label="Close"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
