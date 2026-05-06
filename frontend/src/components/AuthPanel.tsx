import { AccountInfo } from "@azure/msal-browser";
import { authConfig } from "../auth";

interface AuthPanelProps {
  account: AccountInfo | null;
  isReady: boolean;
  onSignIn: () => void;
  onSignOut: () => void;
}

function AuthPanel({ account, isReady, onSignIn, onSignOut }: AuthPanelProps) {
  if (!authConfig.enabled) {
    return (
      <section className="auth-panel">
        <div>
          <strong>Demo mode</strong>
          <span>Microsoft Entra sign-in is not configured locally.</span>
        </div>
      </section>
    );
  }

  return (
    <section className="auth-panel">
      <div>
        <strong>{account ? "Signed in" : "Microsoft sign-in required"}</strong>
        <span>{account?.username ?? "Use your university Microsoft account before submitting drafts."}</span>
      </div>
      <button type="button" className="secondary-button" onClick={account ? onSignOut : onSignIn} disabled={!isReady}>
        {account ? "Sign out" : "Sign in with Microsoft"}
      </button>
    </section>
  );
}

export default AuthPanel;
