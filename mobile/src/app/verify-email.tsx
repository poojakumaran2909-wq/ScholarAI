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

import { router, useLocalSearchParams } from "expo-router";

const API_URL = "http://10.43.36.85:8000";

export default function VerifyEmailScreen() {
  const params = useLocalSearchParams();

  const email =
    typeof params.email === "string"
      ? params.email
      : "";

  const [verificationCode, setVerificationCode] =
    useState("");

  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] =
    useState(false);

  // ============================================================
  // VERIFY EMAIL
  // ============================================================

  const handleVerifyEmail = async () => {
    if (!email) {
      Alert.alert(
        "Email Missing",
        "Please go back and register again."
      );
      return;
    }

    if (verificationCode.length !== 6) {
      Alert.alert(
        "Invalid Code",
        "Please enter the 6-digit verification code."
      );
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(
        `${API_URL}/auth/verify-email`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email.trim().toLowerCase(),
            verification_code: verificationCode,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Email verification failed."
        );
      }

      Alert.alert(
        "Email Verified",
        "Your email has been verified successfully. You can now login.",
        [
          {
            text: "Go to Login",
            onPress: () => {
              router.replace("/login");
            },
          },
        ]
      );

    } catch (error: any) {
      console.log(
        "Email verification error:",
        error
      );

      Alert.alert(
        "Verification Failed",
        error?.message ||
          "Something went wrong. Please try again."
      );

    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // RESEND VERIFICATION CODE
  // ============================================================

  const handleResendCode = async () => {
    if (!email) {
      Alert.alert(
        "Email Missing",
        "Please go back and register again."
      );
      return;
    }

    try {
      setResendLoading(true);

      const response = await fetch(
        `${API_URL}/auth/resend-verification`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email.trim().toLowerCase(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not resend verification code."
        );
      }

      Alert.alert(
        "Code Sent",
        data.message ||
          "A new verification code has been sent to your email."
      );

    } catch (error: any) {
      console.log(
        "Resend verification error:",
        error
      );

      Alert.alert(
        "Resend Failed",
        error?.message ||
          "Something went wrong. Please try again."
      );

    } finally {
      setResendLoading(false);
    }
  };

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

        {/* HEADER */}

        <View style={styles.header}>

          <Text style={styles.logo}>
            ScholarAI
          </Text>

          <Text style={styles.title}>
            Verify Your Email
          </Text>

          <Text style={styles.subtitle}>
            We've sent a 6-digit verification code
            to your email.
          </Text>

        </View>

        {/* EMAIL */}

        <View style={styles.emailBox}>

          <Text style={styles.emailLabel}>
            Verification email
          </Text>

          <Text style={styles.emailText}>
            {email}
          </Text>

        </View>

        {/* FORM */}

        <View style={styles.form}>

          <Text style={styles.label}>
            Verification Code
          </Text>

          <TextInput
            style={styles.input}
            placeholder="Enter 6-digit code"
            placeholderTextColor="#9ca3af"
            value={verificationCode}
            onChangeText={(text) => {
              const numbersOnly =
                text.replace(/[^0-9]/g, "");

              setVerificationCode(
                numbersOnly.slice(0, 6)
              );
            }}
            keyboardType="number-pad"
            maxLength={6}
            textAlign="center"
            autoFocus
          />

          {/* VERIFY BUTTON */}

          <TouchableOpacity
            style={[
              styles.verifyButton,
              loading &&
                styles.buttonDisabled,
            ]}
            onPress={handleVerifyEmail}
            disabled={loading}
          >

            {loading ? (
              <ActivityIndicator
                color="#ffffff"
              />
            ) : (
              <Text style={styles.buttonText}>
                Verify Email
              </Text>
            )}

          </TouchableOpacity>

          {/* RESEND */}

          <View style={styles.resendContainer}>

            <Text style={styles.resendText}>
              Didn't receive the code?
            </Text>

            <TouchableOpacity
              onPress={handleResendCode}
              disabled={resendLoading}
            >

              {resendLoading ? (
                <ActivityIndicator
                  size="small"
                  color="#2563eb"
                />
              ) : (
                <Text style={styles.resendButton}>
                  Resend Code
                </Text>
              )}

            </TouchableOpacity>

          </View>

          {/* LOGIN */}

          <TouchableOpacity
            style={styles.loginButton}
            onPress={() =>
              router.replace("/login")
            }
          >

            <Text style={styles.loginText}>
              Already verified?{" "}
              <Text style={styles.loginHighlight}>
                Login
              </Text>
            </Text>

          </TouchableOpacity>

        </View>

      </View>
    </KeyboardAvoidingView>
  );
}


// ============================================================
// STYLES
// ============================================================

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
    marginBottom: 28,
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
    lineHeight: 22,
    color: "#6b7280",
  },

  emailBox: {
    backgroundColor: "#f3f4f6",
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
  },

  emailLabel: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 4,
  },

  emailText: {
    fontSize: 15,
    fontWeight: "600",
    color: "#111827",
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
    height: 58,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 24,
    fontWeight: "700",
    letterSpacing: 8,
    color: "#111827",
    backgroundColor: "#f9fafb",
  },

  verifyButton: {
    height: 52,
    borderRadius: 12,
    backgroundColor: "#2563eb",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 28,
  },

  buttonDisabled: {
    opacity: 0.7,
  },

  buttonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },

  resendContainer: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 5,
    marginTop: 22,
  },

  resendText: {
    color: "#6b7280",
    fontSize: 14,
  },

  resendButton: {
    color: "#2563eb",
    fontSize: 14,
    fontWeight: "700",
  },

  loginButton: {
    alignItems: "center",
    marginTop: 22,
  },

  loginText: {
    color: "#6b7280",
    fontSize: 14,
  },

  loginHighlight: {
    color: "#2563eb",
    fontWeight: "700",
  },

});