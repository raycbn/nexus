import { cn } from '../utils/helpers';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'status' | 'severity';
  value?: string;
  className?: string;
}

export function Badge({ children, variant = 'default', value, className }: BadgeProps) {
  let variantClass = 'badge';

  if (variant === 'status' && value) {
    variantClass = cn('badge', {
      'badge-detected': value === 'detected',
      'badge-investigating': value === 'investigating',
      'badge-identified': value === 'identified',
      'badge-monitoring': value === 'monitoring',
      'badge-resolved': value === 'resolved',
      'badge-closed': value === 'closed',
    });
  }

  if (variant === 'severity' && value) {
    variantClass = cn('badge', {
      'badge-low': value === 'low',
      'badge-medium': value === 'medium',
      'badge-high': value === 'high',
      'badge-critical': value === 'critical',
    });
  }

  return (
    <span className={cn(variantClass, className)}>
      {children}
    </span>
  );
}