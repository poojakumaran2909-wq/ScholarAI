import * as SecureStore from "expo-secure-store";

const API_URL = "http://10.43.36.85:8000";

const ACCESS_TOKEN_KEY = "scholarai_access_token";
const REFRESH_TOKEN_KEY = "scholarai_refresh_token";
const USER_KEY = "scholarai_user";

export type AuthUser = {
  id: string;
  email: string;
  is_verified: boolean;
  created_at: string;
};

// ==========================================================
// SAVE AUTH DATA
// ==========================================================

export async function saveAuthData(
  accessToken: string,
  refreshToken: string,
  user: AuthUser
) {
  await SecureStore.setItemAsync(
    ACCESS_TOKEN_KEY,
    accessToken
  );

  await SecureStore.setItemAsync(
    REFRESH_TOKEN_KEY,
    refreshToken
  );

  await SecureStore.setItemAsync(
    USER_KEY,
    JSON.stringify(user)
  );
}

// ==========================================================
// GET ACCESS TOKEN
// ==========================================================

export async function getAccessToken() {
  return await SecureStore.getItemAsync(
    ACCESS_TOKEN_KEY
  );
}

// ==========================================================
// GET REFRESH TOKEN
// ==========================================================

export async function getRefreshToken() {
  return await SecureStore.getItemAsync(
    REFRESH_TOKEN_KEY
  );
}

// ==========================================================
// GET STORED USER
// ==========================================================

export async function getStoredUser(): Promise<AuthUser | null> {
  const user = await SecureStore.getItemAsync(
    USER_KEY
  );

  if (!user) {
    return null;
  }

  try {
    return JSON.parse(user);
  } catch {
    return null;
  }
}

// ==========================================================
// REFRESH ACCESS TOKEN
// ==========================================================

export async function refreshAccessToken(): Promise<string | null> {
  try {
    const refreshToken =
      await getRefreshToken();

    if (!refreshToken) {
      return null;
    }

    const response = await fetch(
      `${API_URL}/auth/refresh`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      console.log(
        "Token refresh failed:",
        data.detail
      );

      await clearAuthData();

      return null;
    }

    const newAccessToken =
      data.access_token;

    if (!newAccessToken) {
      console.log(
        "Refresh response did not contain access token."
      );

      await clearAuthData();

      return null;
    }

    await SecureStore.setItemAsync(
      ACCESS_TOKEN_KEY,
      newAccessToken
    );

    return newAccessToken;

  } catch (error) {
    console.log(
      "Token refresh error:",
      error
    );

    return null;
  }
}

// ==========================================================
// AUTHENTICATED FETCH
// ==========================================================
//
// Use this function for protected API requests.
//
// It will:
// 1. Get current access token
// 2. Send request
// 3. If 401 → refresh token
// 4. Retry request with new access token
//
// ==========================================================

export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {

  let accessToken =
    await getAccessToken();

  if (!accessToken) {
    throw new Error(
      "No access token available."
    );
  }

  const makeRequest = async (
    token: string
  ) => {
    const headers = new Headers(
      options.headers
    );

    headers.set(
      "Authorization",
      `Bearer ${token}`
    );

    return await fetch(
      url,
      {
        ...options,
        headers,
      }
    );
  };

  // First request
  let response =
    await makeRequest(accessToken);

  // Token still valid
  if (response.status !== 401) {
    return response;
  }

  // Access token expired
  console.log(
    "Access token expired. Refreshing..."
  );

  const newAccessToken =
    await refreshAccessToken();

  // Refresh token also invalid/expired
  if (!newAccessToken) {
    throw new Error(
      "SESSION_EXPIRED"
    );
  }

  accessToken =
    newAccessToken;

  // Retry original request
  response =
    await makeRequest(accessToken);

  return response;
}

// ==========================================================
// CLEAR AUTH DATA / LOGOUT
// ==========================================================

export async function clearAuthData() {
  await SecureStore.deleteItemAsync(
    ACCESS_TOKEN_KEY
  );

  await SecureStore.deleteItemAsync(
    REFRESH_TOKEN_KEY
  );

  await SecureStore.deleteItemAsync(
    USER_KEY
  );
}