/**
 * @file React error boundary for unexpected render failures.
 */
import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/**
 * Catches uncaught React render errors and shows a recovery screen.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('UI crash:', error, info.componentStack)
  }

  private handleReload = () => {
    this.setState({ error: null })
    window.location.assign('/')
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary">
          <h1>Something went wrong</h1>
          <p>The page hit an unexpected error. You can reload and continue.</p>
          <p className="error-boundary-detail">{this.state.error.message}</p>
          <button type="button" className="btn btn-primary" onClick={this.handleReload}>
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
