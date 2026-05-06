import {
  AccountInfo,
  AuthenticationResult,
  InteractionRequiredAuthError,
  PublicClientApplication
} from "@azure/msal-browser";

const clientId = import.meta.env.VITE_MSAL_CLIENT_ID as string | undefined;
const tenantId = (import.meta.env.VITE_MSAL_TENANT_ID as string | undefined) || "organizations";
const apiScope = import.meta.env.VITE_API_SCOPE as string | undefined;

export const authConfig = {
  enabled: Boolean(clientId),
  apiScope,
  tenantId
};

export const msalInstance = clientId
  ? new PublicClientApplication({
      auth: {
        clientId,
        authority: `https://login.microsoftonline.com/${tenantId}`,
        redirectUri: window.location.origin
      },
      cache: {
        cacheLocation: "sessionStorage"
      }
    })
  : null;

const baseScopes = ["openid", "profile", "email"];

export const loginRequest = {
  scopes: apiScope ? [...baseScopes, apiScope] : baseScopes
};

export async function initializeAuth(): Promise<AccountInfo | null> {
  if (!msalInstance) return null;
  await msalInstance.initialize();
  const redirectResult = await msalInstance.handleRedirectPromise();
  if (redirectResult?.account) {
    msalInstance.setActiveAccount(redirectResult.account);
    return redirectResult.account;
  }

  const account = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0] ?? null;
  if (account) msalInstance.setActiveAccount(account);
  return account;
}

export async function signIn(): Promise<AccountInfo> {
  if (!msalInstance) throw new Error("Microsoft sign-in is not configured.");
  const result = await msalInstance.loginPopup(loginRequest);
  msalInstance.setActiveAccount(result.account);
  if (!result.account) throw new Error("Microsoft sign-in did not return an account.");
  return result.account;
}

export async function signOut(): Promise<void> {
  if (!msalInstance) return;
  const account = msalInstance.getActiveAccount();
  if (account) {
    await msalInstance.logoutPopup({ account });
  }
}

export async function getAccessToken(account: AccountInfo | null): Promise<string | undefined> {
  if (!msalInstance || !authConfig.apiScope) return undefined;
  if (!account) throw new Error("Please sign in before generating feedback.");

  const request = { scopes: [authConfig.apiScope], account };
  try {
    const result: AuthenticationResult = await msalInstance.acquireTokenSilent(request);
    return result.accessToken;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      const result = await msalInstance.acquireTokenPopup(request);
      return result.accessToken;
    }
    throw error;
  }
}
