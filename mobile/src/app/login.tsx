import React, { useState } from "react";

import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { router } from "expo-router";

import { login } from "../services/authService";

const API_URL = "http://10.43.36.85:8000";

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);

  // --------------------------------------------------
  // LOGIN
  // --------------------------------------------------

  const handleLogin = async () => {
    if (!email.trim()) {
      Alert.alert(
        "Missing Email",
        "Please enter your email."
      );
      return;
    }

    if (!password) {
      Alert.alert(
        "Missing Password",
        "Please enter your password."
      );
      return;
    }

    try {
      setLoading(true);

      await login(
        email.trim(),
        password
      );

      // Login successful
      router.replace("/");

    } catch (error: any) {
      console.log(
        "Login error:",
        error
      );

      Alert.alert(
        "Login Failed",
        error?.message ||
          "Invalid email or password."
      );

    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // FORGOT PASSWORD
  // --------------------------------------------------

  const handleForgotPassword = async () => {
    if (!email.trim()) {
      Alert.alert(
        "Enter Email",
        "Please enter your registered email address first."
      );
      return;
    }

    try {
      setForgotLoading(true);

      const response = await fetch(
        `${API_URL}/auth/forgot-password`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            email: email.trim(),
          }),
        }
      );

      const data = await response.json();

      console.log(
        "Forgot password response:",
        data
      );

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Unable to process password reset request."
        );
      }

      Alert.alert(
        "Password Reset",
        data?.message ||
          "If an account with this email exists, a password reset request has been created.",
        [
          {
            text: "Continue",
            onPress: () => {
              router.push({
                pathname: "/reset-password",
                params: {
                  email: email.trim(),
                },
              });
            },
          },
        ]
      );

    } catch (error: any) {
      console.log(
        "Forgot password error:",
        error
      );

      Alert.alert(
        "Reset Password",
        error?.message ||
          "Something went wrong. Please try again."
      );

    } finally {
      setForgotLoading(false);
    }
  };

  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={
        Platform.OS === "ios"
          ? "padding"
          : undefined
      }
    >

      <View style={styles.content}>

        {/* LOGO / TITLE */}

        <View style={styles.header}>

          <Text style={styles.logo}>
            ScholarAI
          </Text>

          <Text style={styles.title}>
            Welcome Back
          </Text>

          <Text style={styles.subtitle}>
            Find scholarships that match you
          </Text>

        </View>


        {/* FORM */}

        <View style={styles.form}>

          {/* EMAIL */}

          <Text style={styles.label}>
            Email
          </Text>

          <TextInput
            style={styles.input}
            placeholder="Enter your email"
            placeholderTextColor="#9ca3af"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            autoCorrect={false}
          />


          {/* PASSWORD */}

          <Text style={styles.label}>
            Password
          </Text>

          <TextInput
            style={styles.input}
            placeholder="Enter your password"
            placeholderTextColor="#9ca3af"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
          />


          {/* FORGOT PASSWORD */}

          <TouchableOpacity
            style={styles.forgotButton}
            onPress={handleForgotPassword}
            disabled={
              loading ||
              forgotLoading
            }
          >

            {forgotLoading ? (

              <ActivityIndicator
                size="small"
                color="#2563eb"
              />

            ) : (

              <Text style={styles.forgotText}>
                Forgot Password?
              </Text>

            )}

          </TouchableOpacity>


          {/* LOGIN BUTTON */}

          <TouchableOpacity
            style={[
              styles.loginButton,
              loading &&
                styles.loginButtonDisabled,
            ]}
            onPress={handleLogin}
            disabled={
              loading ||
              forgotLoading
            }
          >

            {loading ? (

              <ActivityIndicator
                color="#ffffff"
              />

            ) : (

              <Text style={styles.loginButtonText}>
                Login
              </Text>

            )}

          </TouchableOpacity>


          {/* REGISTER */}

          <TouchableOpacity
            style={styles.registerButton}
            onPress={() => router.push("/register")}
            disabled={
              loading ||
              forgotLoading
            }
          >

            <Text style={styles.registerText}>
              Don't have an account?{" "}

              <Text style={styles.registerHighlight}>
                Create Account
              </Text>
            </Text>

          </TouchableOpacity>

        </View>

      </View>

    </KeyboardAvoidingView>
  );
}


// --------------------------------------------------
// STYLES
// --------------------------------------------------

const styles = StyleSheet.create({

  container: {
    flex: 1,
    backgroundColor: "#ffffff",
  },

  content: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 28,
  },

  header: {
    marginBottom: 40,
  },

  logo: {
    fontSize: 32,
    fontWeight: "800",
    color: "#2563eb",
    marginBottom: 18,
  },

  title: {
    fontSize: 28,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 8,
  },

  subtitle: {
    fontSize: 15,
    color: "#6b7280",
  },

  form: {
    width: "100%",
  },

  label: {
    fontSize: 14,
    fontWeight: "600",
    color: "#374151",
    marginBottom: 8,
    marginTop: 16,
  },

  input: {
    height: 52,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    color: "#111827",
    backgroundColor: "#f9fafb",
  },

  // --------------------------------------------------
  // FORGOT PASSWORD
  // --------------------------------------------------

  forgotButton: {
    alignSelf: "flex-end",
    marginTop: 12,
    minHeight: 24,
    justifyContent: "center",
  },

  forgotText: {
    color: "#2563eb",
    fontSize: 14,
    fontWeight: "600",
  },

  // --------------------------------------------------
  // LOGIN
  // --------------------------------------------------

  loginButton: {
    height: 52,
    borderRadius: 12,
    backgroundColor: "#2563eb",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 20,
  },

  loginButtonDisabled: {
    opacity: 0.7,
  },

  loginButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },

  // --------------------------------------------------
  // REGISTER
  // --------------------------------------------------

  registerButton: {
    alignItems: "center",
    marginTop: 22,
  },

  registerText: {
    color: "#6b7280",
    fontSize: 14,
  },

  registerHighlight: {
    color: "#2563eb",
    fontWeight: "700",
  },

});