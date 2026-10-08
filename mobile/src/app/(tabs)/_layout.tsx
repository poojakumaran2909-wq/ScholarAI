import React, { useEffect, useState } from "react";

import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from "@react-navigation/native";

import { Redirect, Tabs } from "expo-router";

import {
  ActivityIndicator,
  View,
  useColorScheme,
} from "react-native";

import { getAccessToken } from "../../services/authService";

export default function TabsLayout() {
  const colorScheme = useColorScheme();

  const [checkingAuth, setCheckingAuth] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const checkAuthentication = async () => {
      try {
        const token = await getAccessToken();

        setIsLoggedIn(!!token);
      } catch (error) {
        console.log(
          "Authentication check failed:",
          error
        );

        setIsLoggedIn(false);
      } finally {
        setCheckingAuth(false);
      }
    };

    checkAuthentication();
  }, []);

  if (checkingAuth) {
    return (
      <View
        style={{
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!isLoggedIn) {
    return <Redirect href="/login" />;
  }

  return (
    <ThemeProvider
      value={
        colorScheme === "dark"
          ? DarkTheme
          : DefaultTheme
      }
    >
      <Tabs
        screenOptions={{
          headerShown: false,
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: "Home",
          }}
        />

        <Tabs.Screen
          name="explore"
          options={{
            title: "Explore",
          }}
        />

        <Tabs.Screen
          name="matches"
          options={{
            title: "Matches",
          }}
        />

        <Tabs.Screen
          name="saved"
          options={{
            title: "Saved",
          }}
        />

        <Tabs.Screen
          name="profile"
          options={{
            title: "Profile",
          }}
        />
      </Tabs>
    </ThemeProvider>
  );
}


