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

export default function ResetPasswordScreen() {
  const params = useLocalSearchParams();

  const [email, setEmail] = useState(
    typeof params.email === "string"
      ? params.email
      : ""
  );

  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);

  // --------------------------------------------------
  // RESET PASSWORD
  // --------------------------------------------------

  const handleResetPassword = async () => {
    // EMAIL
    if (!email.trim()) {
      Alert.alert(
        "Missing Email",
        "Please enter your registered email."
      );
      return;
    }

    // TOKEN
    if (!resetToken.trim()) {
      Alert.alert(
        "Missing Reset Token",
        "Please enter the reset token from your email."
      );
      return;
    }

    // PASSWORD
    if (!newPassword) {
      Alert.alert(
        "Missing Password",
        "Please enter your new password."
      );
      return;
    }

    // PASSWORD LENGTH
    if (newPassword.length < 8) {
      Alert.alert(
        "Weak Password",
        "Password must contain at least 8 characters."
      );
      return;
    }

    // CONFIRM PASSWORD
    if (!confirmPassword) {
      Alert.alert(
        "Confirm Password",
        "Please confirm your new password."
      );
      return;
    }

    // PASSWORD MATCH
    if (newPassword !== confirmPassword) {
      Alert.alert(
        "Password Mismatch",
        "New password and confirm password do not match."
      );
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(
        `${API_URL}/auth/reset-password`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            email: email.trim(),
            reset_token: resetToken.trim(),
            new_password: newPassword,
          }),
        }
      );

      const data = await response.json();

      console.log(
        "Reset password response:",
        data
      );

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Unable to reset password."
        );
      }

      // ----------------------------------------------
      // SUCCESS
      // ----------------------------------------------

      Alert.alert(
        "Password Reset Successful",
        "Your password has been changed successfully. You can now login with your new password.",
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
        "Reset password error:",
        error
      );

      Alert.alert(
        "Reset Failed",
        error?.message ||
          "Something went wrong. Please try again."
      );

    } finally {
      setLoading(false);
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

        {/* HEADER */}

        <View style={styles.header}>

          <Text style={styles.logo}>
            ScholarAI
          </Text>

          <Text style={styles.title}>
            Reset Password
          </Text>

          <Text style={styles.subtitle}>
            Enter the token sent to your email
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


          {/* RESET TOKEN */}

          <Text style={styles.label}>
            Reset Token
          </Text>

          <TextInput
            style={[
              styles.input,
              styles.tokenInput,
            ]}
            placeholder="Paste token from email"
            placeholderTextColor="#9ca3af"
            value={resetToken}
            onChangeText={setResetToken}
            autoCapitalize="none"
            autoCorrect={false}
            multiline
          />


          {/* NEW PASSWORD */}

          <Text style={styles.label}>
            New Password
          </Text>

          <TextInput
            style={styles.input}
            placeholder="Enter new password"
            placeholderTextColor="#9ca3af"
            value={newPassword}
            onChangeText={setNewPassword}
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
          />


          {/* CONFIRM PASSWORD */}

          <Text style={styles.label}>
            Confirm Password
          </Text>

          <TextInput
            style={styles.input}
            placeholder="Confirm new password"
            placeholderTextColor="#9ca3af"
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
          />


          {/* RESET BUTTON */}

          <TouchableOpacity
            style={[
              styles.resetButton,
              loading &&
                styles.resetButtonDisabled,
            ]}
            onPress={handleResetPassword}
            disabled={loading}
          >

            {loading ? (

              <ActivityIndicator
                color="#ffffff"
              />

            ) : (

              <Text style={styles.resetButtonText}>
                Reset Password
              </Text>

            )}

          </TouchableOpacity>


          {/* BACK TO LOGIN */}

          <TouchableOpacity
            style={styles.loginButton}
            onPress={() => router.replace("/login")}
            disabled={loading}
          >

            <Text style={styles.loginText}>
              Back to Login
            </Text>

          </TouchableOpacity>

        </View>

      </View>

    </KeyboardAvoidingView>
  );
}


// ======================================================
// STYLES
// ======================================================

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
    marginBottom: 32,
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

  tokenInput: {
    height: 70,
    paddingTop: 14,
    textAlignVertical: "top",
  },

  resetButton: {
    height: 52,
    borderRadius: 12,
    backgroundColor: "#2563eb",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 28,
  },

  resetButtonDisabled: {
    opacity: 0.7,
  },

  resetButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },

  loginButton: {
    alignItems: "center",
    marginTop: 22,
  },

  loginText: {
    color: "#2563eb",
    fontSize: 14,
    fontWeight: "600",
  },

});