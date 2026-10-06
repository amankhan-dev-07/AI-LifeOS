import React from 'react';

/**
 * Top-level error boundary.
 *
 * Without this, any uncaught render error unmounts the entire React tree and
 * leaves a blank white page — in production there is no console overlay to
 * explain why, so a single bad response shape looks like "the app is broken"
 * with no recovery path short of a manual refresh.
 *
 * The boundary deliberately renders no stack trace or error message from the
 * thrown value: those can contain response payloads, and this is a screen any
 * visitor can see. The detail goes to the browser console for the developer.
 */

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
}

class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    // Server-side only. In production this is the single place a render
    // failure is recorded.
    console.error('Unhandled UI error:', error, info.componentStack);
  }

  handleReset = (): void => {
    this.setState({ hasError: false });
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div className="shell-bg flex min-h-screen items-center justify-center p-8">
          <div className="flex max-w-md flex-col items-center gap-4 text-center">
            <h1 className="text-lg font-semibold text-[rgb(var(--text-primary))]">
              Something went wrong
            </h1>
            <p className="text-sm text-[rgb(var(--text-tertiary))]">
              The app hit an unexpected error. Reloading usually clears it. Your
              data is safe — nothing was lost.
            </p>
            <button
              type="button"
              onClick={this.handleReset}
              className="btn-primary rounded-xl px-5 py-2 text-sm font-medium"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
