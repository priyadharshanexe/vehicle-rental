import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { signIn } from './api'
import { Busy, Notice } from './shared'
import { formData, useSession } from './requests'
import heroImage from './assets/studio-car.png'

export function Password({ label, name, autoComplete, required = true }: {
  label: string; name: string; autoComplete: string; required?: boolean
}) {
  const [visible, setVisible] = useState(false)
  return <div className="password"><label>{label}<input type={visible ? 'text' : 'password'} name={name} autoComplete={autoComplete} required={required} /></label>
    <button type="button" className="secondary" aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? 'Hide' : 'Show'}</button></div>
}

export function AuthFrame({ children }: { children: ReactNode }) {
  return <div className="auth-frame"><section className="auth-form">{children}</section>
    <div className="auth-image" style={{ backgroundImage: `url(${heroImage})` }} aria-hidden="true" /></div>
}

export function SignIn() {
  const session = useSession()
  const [params] = useSearchParams()
  const cache = useQueryClient()
  const login = useMutation({
    mutationFn: (data: FormData) => signIn(String(data.get('email')), String(data.get('password')), session.data?.csrf_token ?? ''),
    onSuccess: () => cache.invalidateQueries({ queryKey: ['session'] }),
  })
  const desired = params.get('next')
  const safe = desired?.startsWith('/') && !desired.startsWith('//') && !desired.includes('\\') ? desired : '/dashboard'
  const next = `/app${safe}`
  if (session.isPending) return <Busy />
  if (session.isError) return <Notice error={session.error} />
  if (session.data.user) return <Navigate to={safe} replace />
  return <AuthFrame><h1>Sign in</h1>
    <form onSubmit={event => login.mutate(formData(event))} className="fields">
      <label>Email<input type="email" name="email" autoComplete="email" required /></label>
      <Password label="Password" name="password" autoComplete="current-password" />
      <Notice error={login.error} /><button disabled={login.isPending}>{login.isPending ? "Signing in…" : "Sign in"}</button>
    </form>
    {session.data.google_enabled && <form method="post" action="/accounts/google/login/" className="google">
      <input type="hidden" name="csrfmiddlewaretoken" value={session.data.csrf_token} />
      <input type="hidden" name="next" value={next} />
      <button className="secondary">Continue with Google</button>
    </form>}
    <p><Link to="/reset-password">Forgot your password?</Link></p>
    <p><Link to={`/register?next=${encodeURIComponent(safe)}`}>Create an account</Link></p>
  </AuthFrame>
}
