import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { useAuthStore } from '../store/authStore';
import { api } from '../api/trafitwin';

export function LoginGate() {
  const { token, email, login, logout } = useAuthStore();

  async function handleSuccess(credentialResponse: CredentialResponse) {
    if (!credentialResponse.credential) return;
    try {
      const { access_token, email } = await api.loginWithGoogle(credentialResponse.credential);
      login(access_token, email);
    } catch (e) {
      console.error('Google login failed:', e);
    }
  }

  if (token) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#1A2230] border border-[#2A3545] text-xs font-mono text-[#8BA0BA]">
        <span className="text-[#10B981]">●</span>
        <span className="truncate max-w-[160px]">{email ?? 'Signed in'}</span>
        <button
          onClick={logout}
          className="text-[#8BA0BA] hover:text-[#EF4444] transition-colors"
          aria-label="Sign out"
        >
          SIGN OUT
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center">
      <GoogleLogin onSuccess={handleSuccess} onError={() => console.error('Google login failed')} theme="filled_black" size="medium" />
    </div>
  );
}
