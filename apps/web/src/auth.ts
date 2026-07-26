import { UserManager, WebStorageStateStore } from "oidc-client-ts";

const authority = import.meta.env.VITE_OIDC_AUTHORITY;
const clientId = import.meta.env.VITE_OIDC_CLIENT_ID;
const redirectUri = import.meta.env.VITE_OIDC_REDIRECT_URI ?? window.location.origin;
const scope = import.meta.env.VITE_OIDC_SCOPE ?? "openid profile";
const tokenStorageKey = "wiki-ai-rag-access-token";

const userManager =
  authority && clientId
    ? new UserManager({
        authority,
        client_id: clientId,
        redirect_uri: redirectUri,
        post_logout_redirect_uri: window.location.origin,
        response_type: "code",
        scope,
        automaticSilentRenew: true,
        userStore: new WebStorageStateStore({ store: window.sessionStorage }),
      })
    : null;

export function oidcIsConfigured(): boolean {
  return userManager !== null;
}

export async function initializeAuthentication(): Promise<boolean> {
  if (!userManager) return false;
  if (new URLSearchParams(window.location.search).has("code")) {
    await userManager.signinRedirectCallback();
    window.history.replaceState({}, document.title, window.location.pathname);
  }
  const user = await userManager.getUser();
  if (user && !user.expired) {
    sessionStorage.setItem(tokenStorageKey, user.access_token);
    return true;
  }
  sessionStorage.removeItem(tokenStorageKey);
  return false;
}

export async function signIn(): Promise<void> {
  if (userManager) await userManager.signinRedirect();
}

export async function signOut(): Promise<void> {
  sessionStorage.removeItem(tokenStorageKey);
  if (userManager) await userManager.signoutRedirect();
}
