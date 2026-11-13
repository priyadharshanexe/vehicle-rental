import { Breadcrumb } from './Breadcrumb'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams, useSearchParams } from 'react-router-dom'
import { api, authRequest } from './api'
import type { Session } from './api'
import { AuthFrame, Password } from './Auth'
import { Busy, Notice } from './shared'

type Screen = 'signup' | 'request-reset' | 'reset' | 'verify' | 'account'

const screens = {
  signup: { title: 'Create an account', button: 'Create account', endpoint: 'auth/signup',
    done: 'Check your inbox for a link to verify your email.' },
  'request-reset': { title: 'Reset your password', button: 'Send reset link', endpoint: 'auth/password/request',
    done: 'If an account matches that email, you’ll receive a password reset link.' },
  reset: { title: 'Choose a new password', button: 'Save new password', endpoint: 'auth/password/reset',
    done: 'Password updated. You can now sign in.' },
  verify: { title: 'Verify your email', button: 'Verify email', endpoint: 'auth/email/verify',
    done: 'Email verified. You can now sign in.' },
  account: { title: 'My account', button: 'Update password', endpoint: 'account/password/change',
    done: 'Password updated.' },
} satisfies Record<Screen, { title: string; button: string; endpoint: string; done: string }>

export default function AccountScreen({ screen }: { screen: Screen }) {
  const session = useQuery({ queryKey: ['session'], queryFn: () => api<Session>('session/') })
  const cache = useQueryClient()
  const { key } = useParams()
  const [params] = useSearchParams()
  const page = screens[screen]
  const write = useMutation({
    mutationFn: (data: Record<string, string>) => authRequest(page.endpoint, data, session.data?.csrf_token ?? '',
      { verificationPending: screen === 'signup', signedOutSuccess: screen === 'verify' || screen === 'reset' }),
    onSuccess: () => cache.invalidateQueries({ queryKey: ['session'] }),
  })
  const needsEmail = screen === 'signup' || screen === 'request-reset'
  const needsPassword = screen === 'signup' || screen === 'reset' || screen === 'account'
  const next = params.get('next')
  const content = <>
     {screen !== 'account' && <Breadcrumb to={next ? `/sign-in?next=${encodeURIComponent(next)}` : '/sign-in'} parent="Sign in" current={page.title} />}
    <h1>{page.title}</h1>
    {screen === 'account' && <><p>Signed in as <strong>{session.data?.user?.name}</strong></p>
      <div className="quick-links"><a href="/accounts/email/">Manage email addresses →</a><a href="/accounts/3rdparty/">Connected accounts →</a></div><h2>Change password</h2></>}
    {screen === 'verify' && <p>Confirm the email address associated with your Motorlane account.</p>}
    {screen === 'request-reset' && <p>Enter your account email to request a password reset link.</p>}
    {session.isPending && <Busy />}<Notice error={session.error} />
    {write.isSuccess ? <p role="status">{page.done}</p> : <form className="fields" onSubmit={event => {
      event.preventDefault()
      const fields = new FormData(event.currentTarget)
      const data: Record<string, string> = {}
      for (const [name, value] of fields) if (typeof value === 'string' && value) data[name] = value
      if (key) data.key = key
      write.mutate(data)
    }}>
      {needsEmail && <label>Email<input type="email" name="email" autoComplete="email" required /></label>}
      {screen === 'account' && <Password label="Current password" name="current_password" autoComplete="current-password" required={false} />}
      {needsPassword && <Password label="New password" name={screen === 'account' ? 'new_password' : 'password'} autoComplete="new-password" />}
      {write.error && <p className="error" role="alert">{write.error.message}</p>}
      <button disabled={!session.data || write.isPending}>{write.isPending ? 'Submitting…' : page.button}</button>
    </form>}

  </>
  return screen === 'account' ? <section className="panel account-settings">{content}</section> : <AuthFrame>{content}</AuthFrame>
}
