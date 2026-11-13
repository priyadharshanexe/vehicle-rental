import { Component } from 'react'
import type { ReactNode } from 'react'

export default class RouteErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return <section className="panel" role="alert">
      <h1>This page couldn’t load</h1>
      <p>Reload to try again.</p>
      <button onClick={() => window.location.reload()}>Reload page</button>
    </section>
  }
}
