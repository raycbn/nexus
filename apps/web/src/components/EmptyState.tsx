import { cn } from '../utils/helpers';
import { Button } from './Button';
import { AlertTriangle, RefreshCw, XCircle } from 'lucide-react';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorState({ message, onRetry, onDismiss, className }: ErrorStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center p-8 text-center gap-4', className)}>
      <div className="p-3 bg-red-900/20 rounded-full text-nexus-danger">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-nexus-text">Unable to load</h3>
        <p className="mt-1 text-nexus-textMuted text-sm max-w-xs">{message}</p>
      </div>
      <div className="flex gap-2">
        {onRetry && (
          <Button variant="primary" size="sm" onClick={onRetry}>
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
        )}
        {onDismiss && (
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            <XCircle className="h-4 w-4" />
            Dismiss
          </Button>
        )}
      </div>
    </div>
  );
}

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center p-8 text-center gap-4', className)}>
      <div className="p-3 bg-nexus-surfaceHover rounded-full text-nexus-textMuted">
        {icon}
      </div>
      <div>
        <h3 className="text-lg font-semibold text-nexus-text">{title}</h3>
        <p className="mt-1 text-nexus-textMuted text-sm max-w-xs">{description}</p>
      </div>
      {action && (
        <Button variant="primary" size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}