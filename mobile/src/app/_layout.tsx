import React from "react";

import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen
        name="(tabs)"
        options={{
          headerShown: false,
        }}
      />

      <Stack.Screen
        name="login"
        options={{
          headerShown: false,
        }}
      />

      <Stack.Screen
        name="register"
        options={{
          headerShown: false,
        }}
      />

      <Stack.Screen
        name="reset-password"
        options={{
          headerShown: false,
        }}
      />

      <Stack.Screen
        name="verify-email"
        options={{
          headerShown: false,
        }}
      />
    </Stack>
  );
}