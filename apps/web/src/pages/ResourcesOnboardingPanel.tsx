import { InfrastructureOnboarding } from '../components/InfrastructureOnboarding';

export function ResourcesOnboardingPanel({ onComplete, onCancel }: { onComplete: () => void; onCancel: () => void }) {
  return <InfrastructureOnboarding onComplete={onComplete} onCancel={onCancel} />;
}
