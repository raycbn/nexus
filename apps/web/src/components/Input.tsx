import { cn } from '../utils/helpers';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className, id, ...props }: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-nexus-textMuted mb-1.5">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={cn(
          'w-full px-3 py-2 text-sm bg-nexus-surface border rounded-lg text-nexus-text placeholder-nexus-textMuted focus:outline-none focus:ring-2 focus:ring-nexus-primary focus:border-transparent transition-colors',
          error && 'border-nexus-danger focus:ring-nexus-danger',
          !error && 'border-nexus-border hover:border-nexus-borderHover',
          className
        )}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${inputId}-error` : undefined}
        {...props}
      />
      {error && (
        <p id={`${inputId}-error`} className="mt-1.5 text-sm text-nexus-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}