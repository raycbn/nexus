import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { Button, Input, Select, Badge, Card, Modal, Loading, LoadingOverlay, EmptyState, ErrorState } from '@/components';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderWithProviders = (component: React.ReactNode) => {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('Components', () => {
  describe('Button', () => {
    it('renders correctly', () => {
      renderWithProviders(<Button>Click me</Button>);
      expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
    });

    it('shows loading state', () => {
      renderWithProviders(<Button loading>Click me</Button>);
      expect(screen.getByRole('button', { name: 'Click me' })).toBeDisabled();
      expect(screen.getByRole('button')).toContainHTML('svg');
    });

    it('applies variant classes', () => {
      renderWithProviders(<Button variant="secondary">Secondary</Button>);
      expect(screen.getByRole('button')).toHaveClass('bg-nexus-surfaceHover');
    });
  });

  describe('Input', () => {
    it('renders with label', () => {
      renderWithProviders(<Input label="Email" placeholder="Enter email" />);
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    it('shows error message', () => {
      renderWithProviders(<Input label="Email" error="Invalid email" />);
      expect(screen.getByText('Invalid email')).toBeInTheDocument();
    });
  });

  describe('Select', () => {
    it('renders options', () => {
      renderWithProviders(
        <Select
          label="Status"
          options={[{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }]}
          placeholder="Select..."
        />
      );
      expect(screen.getByLabelText('Status')).toBeInTheDocument();
      expect(screen.getByText('Select...')).toBeInTheDocument();
    });
  });

  describe('Badge', () => {
    it('renders status badge', () => {
      renderWithProviders(<Badge variant="status" value="detected">Detected</Badge>);
      expect(screen.getByText('Detected')).toHaveClass('badge-detected');
    });

    it('renders severity badge', () => {
      renderWithProviders(<Badge variant="severity" value="critical">Critical</Badge>);
      expect(screen.getByText('Critical')).toHaveClass('badge-critical');
    });
  });

  describe('Card', () => {
    it('renders children', () => {
      renderWithProviders(<Card>Card content</Card>);
      expect(screen.getByText('Card content')).toBeInTheDocument();
    });

    it('applies hover styles when hover prop is true', () => {
      renderWithProviders(<Card hover>Hoverable</Card>);
      expect(screen.getByText('Hoverable')).toHaveClass('hover:border-nexus-borderHover');
    });
  });

  describe('Modal', () => {
    it('renders when open', () => {
      renderWithProviders(<Modal isOpen={true} onClose={vi.fn()} title="Test Modal">Modal content</Modal>);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Test Modal')).toBeInTheDocument();
      expect(screen.getByText('Modal content')).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      renderWithProviders(<Modal isOpen={false} onClose={vi.fn()} title="Test Modal">Modal content</Modal>);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('closes on overlay click', () => {
      const onClose = vi.fn();
      renderWithProviders(<Modal isOpen={true} onClose={onClose} title="Test Modal">Modal content</Modal>);
      fireEvent.click(screen.getByRole('dialog'));
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Loading', () => {
    it('renders spinner', () => {
      renderWithProviders(<Loading />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('renders overlay with message', () => {
      renderWithProviders(<LoadingOverlay message="Loading data..." />);
      expect(screen.getByText('Loading data...')).toBeInTheDocument();
    });
  });

  describe('EmptyState', () => {
    it('renders icon, title, description', () => {
      renderWithProviders(
        <EmptyState
          icon={<span data-testid="icon">Icon</span>}
          title="No data"
          description="There is no data to show"
        />
      );
      expect(screen.getByTestId('icon')).toBeInTheDocument();
      expect(screen.getByText('No data')).toBeInTheDocument();
      expect(screen.getByText('There is no data to show')).toBeInTheDocument();
    });

    it('renders action button', () => {
      const onClick = vi.fn();
      renderWithProviders(
        <EmptyState
          icon={<span>Icon</span>}
          title="No data"
          description="Description"
          action={{ label: 'Action', onClick }}
        />
      );
      fireEvent.click(screen.getByRole('button', { name: 'Action' }));
      expect(onClick).toHaveBeenCalled();
    });
  });

  describe('ErrorState', () => {
    it('renders error message and retry button', () => {
      const onRetry = vi.fn();
      renderWithProviders(<ErrorState message="Something went wrong" onRetry={onRetry} />);
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: 'Try Again' }));
      expect(onRetry).toHaveBeenCalled();
    });
  });
});