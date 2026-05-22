import React, { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';

const Toast = ({ toast }) => {
  const { removeToast } = useUIStore();
  
  useEffect(() => {
    if (toast.duration > 0) {
      const timer = setTimeout(() => {
        removeToast(toast.id);
      }, toast.duration);
      
      return () => clearTimeout(timer);
    }
  }, [toast.id, toast.duration, removeToast]);
  
  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-amber-400" />;
      default:
        return <Info className="w-5 h-5 text-blue-400" />;
    }
  };
  
  const getBackgroundColor = () => {
    switch (toast.type) {
      case 'success':
        return 'bg-green-900/90 border-green-700';
      case 'error':
        return 'bg-red-900/90 border-red-700';
      case 'warning':
        return 'bg-amber-900/90 border-amber-700';
      default:
        return 'bg-blue-900/90 border-blue-700';
    }
  };
  
  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-lg border shadow-lg backdrop-blur-sm transition-all duration-300 transform ${getBackgroundColor()}`}
      role="alert"
      aria-live="polite"
    >
      <div className="flex-shrink-0 mt-0.5">
        {getIcon()}
      </div>
      
      <div className="flex-1 min-w-0">
        {toast.title && (
          <h4 className="text-sm font-semibold text-white mb-1">
            {toast.title}
          </h4>
        )}
        <p className="text-sm text-gray-200">
          {toast.message}
        </p>
        {toast.action && (
          <button
            onClick={() => {
              toast.action.onClick();
              removeToast(toast.id);
            }}
            className="mt-2 text-sm font-medium text-white hover:underline"
          >
            {toast.action.label}
          </button>
        )}
      </div>
      
      <button
        onClick={() => removeToast(toast.id)}
        className="flex-shrink-0 text-gray-400 hover:text-white transition-colors"
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

const ToastContainer = () => {
  const { toasts } = useUIStore();
  
  if (toasts.length === 0) {
    return null;
  }
  
  return (
    <div
      className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} />
      ))}
    </div>
  );
};

export { Toast, ToastContainer };
