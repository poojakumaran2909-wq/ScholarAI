import React, {
  useCallback,
  useState,
} from "react";

import {
  ActivityIndicator,
  Alert,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import {
  router,
  useFocusEffect,
} from "expo-router";

import {
  cancelScholarshipNotifications,
} from "../../services/notificationService";

import {
  getAccessToken,
  getStoredUser,
  authenticatedFetch,
  clearAuthData,
} from "../../services/authService";

// ============================================================
// BACKEND
// ============================================================

const API_URL = "http://10.43.36.85:8000";

// ============================================================
// TYPES
// ============================================================

type SavedScholarship = {
  id: number;
  email: string;
  scholarship_id: string;
  scholarship_name: string;
  deadline: string | null;
  status:
    | "saved"
    | "applied"
    | "not_applied";
  saved_at: string;
};

// ============================================================
// SCREEN
// ============================================================

export default function SavedScreen() {
  const [scholarships, setScholarships] =
    useState<SavedScholarship[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState("");

  // Logged-in user
  const [email, setEmail] =
    useState<string | null>(null);

  const [accessToken, setAccessToken] =
    useState<string | null>(null);

  // ==========================================================
  // LOAD AUTH DATA
  // ==========================================================

  const loadAuthData = async () => {
    const user = await getStoredUser();
    const token = await getAccessToken();

    if (!user || !token) {
      throw new Error(
        "No logged-in user found. Please login again."
      );
    }

    setEmail(user.email);
    setAccessToken(token);

    return {
      email: user.email,
      token,
    };
  };

  // ==========================================================
  // FETCH SAVED SCHOLARSHIPS
  // ==========================================================

  const fetchSavedScholarships = async (
    showLoader = true,
    userEmail?: string,
    token?: string
  ) => {
    try {
      if (showLoader) {
        setLoading(true);
      }

      setError("");

      const currentEmail =
        userEmail || email;

      const currentToken =
        token || accessToken;

      if (!currentEmail || !currentToken) {
        throw new Error(
          "Authentication information is missing."
        );
      }

      // FIXED:
      // authenticatedFetch is now properly closed.
      const response = await authenticatedFetch(
        `${API_URL}/saved/${encodeURIComponent(
          currentEmail
        )}`
      );

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error(
            "Session expired. Please login again."
          );
        }

        if (response.status === 403) {
          throw new Error(
            "You are not authorized to access these scholarships."
          );
        }

        throw new Error(
          `Server error: ${response.status}`
        );
      }

      const data = await response.json();

      setScholarships(
        data.saved || []
      );

    } catch (err) {
      if (
        err instanceof Error &&
        err.message === "SESSION_EXPIRED"
      ) {
        await clearAuthData();
        router.replace("/login");
        return;
      }

      console.log(
        "Saved scholarship request failed:",
        err
      );

      setError(
        err instanceof Error
          ? err.message
          : "Could not load saved scholarships. Make sure the backend is running."
      );

    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // ==========================================================
  // LOAD WHEN TAB OPENS
  // ==========================================================

  useFocusEffect(
    useCallback(() => {
      const loadData = async () => {
        try {
          const auth =
            await loadAuthData();

          await fetchSavedScholarships(
            false,
            auth.email,
            auth.token
          );

        } catch (err) {
          console.log(
            "Authentication loading failed:",
            err
          );

          setError(
            err instanceof Error
              ? err.message
              : "Please login again."
          );

          setLoading(false);
        }
      };

      loadData();
    }, [])
  );

  // ==========================================================
  // REFRESH
  // ==========================================================

  const onRefresh = async () => {
    setRefreshing(true);

    try {
      const auth =
        await loadAuthData();

      await fetchSavedScholarships(
        false,
        auth.email,
        auth.token
      );

    } catch (err) {
      console.log(
        "Refresh failed:",
        err
      );

      setRefreshing(false);
    }
  };

  // ==========================================================
  // REMOVE SCHOLARSHIP
  // ==========================================================

  const removeScholarship = (
    scholarshipId: string
  ) => {
    Alert.alert(
      "Remove Scholarship",
      "Remove this scholarship from your saved list?",
      [
        {
          text: "Cancel",
          style: "cancel",
        },

        {
          text: "Remove",
          style: "destructive",

          onPress: async () => {
            try {
              const currentEmail = email;

              const currentToken =
                accessToken;

              if (
                !currentEmail ||
                !currentToken
              ) {
                Alert.alert(
                  "Login Required",
                  "Please login again."
                );
                return;
              }

              const response =
                await authenticatedFetch(
                  `${API_URL}/saved/${encodeURIComponent(
                    currentEmail
                  )}/${encodeURIComponent(
                    scholarshipId
                  )}`,
                  {
                    method: "DELETE",
                  }
                );

              if (!response.ok) {
                if (
                  response.status === 401
                ) {
                  throw new Error(
                    "Your session has expired."
                  );
                }

                if (
                  response.status === 403
                ) {
                  throw new Error(
                    "You are not authorized to remove this scholarship."
                  );
                }

                throw new Error(
                  "Failed to remove scholarship"
                );
              }

              // ==================================================
              // CANCEL DEADLINE NOTIFICATIONS
              // ==================================================

              try {
                await cancelScholarshipNotifications(
                  scholarshipId
                );
              } catch (
                notificationError
              ) {
                console.log(
                  "Notification cancellation failed:",
                  notificationError
                );
              }

              // ==================================================
              // UPDATE UI
              // ==================================================

              setScholarships(
                previous =>
                  previous.filter(
                    item =>
                      item.scholarship_id !==
                      scholarshipId
                  )
              );

            } catch (err) {
              if (
                err instanceof Error &&
                err.message ===
                  "SESSION_EXPIRED"
              ) {
                await clearAuthData();
                router.replace("/login");
                return;
              }

              console.log(
                "Remove scholarship error:",
                err
              );

              Alert.alert(
                "Error",
                err instanceof Error
                  ? err.message
                  : "Could not remove scholarship."
              );
            }
          },
        },
      ]
    );
  };

  // ==========================================================
  // MARK AS APPLIED
  // ==========================================================

  const markAsApplied = async (
    scholarshipId: string
  ) => {
    try {
      const currentEmail = email;

      const currentToken =
        accessToken;

      if (
        !currentEmail ||
        !currentToken
      ) {
        Alert.alert(
          "Login Required",
          "Please login again."
        );
        return;
      }

      const response =
        await authenticatedFetch(
          `${API_URL}/saved/${encodeURIComponent(
            currentEmail
          )}/${encodeURIComponent(
            scholarshipId
          )}`,
          {
            method: "PATCH",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              status: "applied",
            }),
          }
        );

      if (!response.ok) {
        let data: any = {};

        try {
          data =
            await response.json();
        } catch {
          // Ignore parsing error
        }

        throw new Error(
          data.detail ||
            "Failed to update status"
        );
      }

      setScholarships(
        previous =>
          previous.map(item =>
            item.scholarship_id ===
            scholarshipId
              ? {
                  ...item,
                  status: "applied",
                }
              : item
          )
      );

    } catch (err) {
      if (
        err instanceof Error &&
        err.message ===
          "SESSION_EXPIRED"
      ) {
        await clearAuthData();
        router.replace("/login");
        return;
      }

      console.log(
        "Update status error:",
        err
      );

      Alert.alert(
        "Error",
        err instanceof Error
          ? err.message
          : "Could not update scholarship status."
      );
    }
  };

  // ==========================================================
  // DEADLINE DISPLAY
  // ==========================================================

  const getDeadlineText = (
    deadline: string | null
  ) => {
    if (!deadline) {
      return {
        text: "📅 Deadline varies",
        urgent: false,
      };
    }

    let deadlineDate: Date | null =
      null;

    // DD-MM-YYYY
    const dashMatch = deadline.match(
      /^(\d{2})-(\d{2})-(\d{4})$/
    );

    if (dashMatch) {
      deadlineDate = new Date(
        Number(dashMatch[3]),
        Number(dashMatch[2]) - 1,
        Number(dashMatch[1])
      );
    }

    // DD/MM/YYYY
    const slashMatch = deadline.match(
      /^(\d{2})\/(\d{2})\/(\d{4})$/
    );

    if (slashMatch) {
      deadlineDate = new Date(
        Number(slashMatch[3]),
        Number(slashMatch[2]) - 1,
        Number(slashMatch[1])
      );
    }

    // YYYY-MM-DD
    const isoMatch = deadline.match(
      /^(\d{4})-(\d{2})-(\d{2})$/
    );

    if (isoMatch) {
      deadlineDate = new Date(
        Number(isoMatch[1]),
        Number(isoMatch[2]) - 1,
        Number(isoMatch[3])
      );
    }

    if (!deadlineDate) {
      return {
        text: `📅 ${deadline}`,
        urgent: false,
      };
    }

    const today = new Date();

    today.setHours(
      0,
      0,
      0,
      0
    );

    deadlineDate.setHours(
      0,
      0,
      0,
      0
    );

    const difference =
      deadlineDate.getTime() -
      today.getTime();

    const daysRemaining =
      Math.ceil(
        difference /
          (1000 * 60 * 60 * 24)
      );

    if (daysRemaining < 0) {
      return {
        text:
          `❌ Expired • ${deadline}`,
        urgent: true,
      };
    }

    if (daysRemaining === 0) {
      return {
        text:
          `🔴 Deadline today • ${deadline}`,
        urgent: true,
      };
    }

    if (daysRemaining <= 3) {
      return {
        text:
          `🔴 ${daysRemaining} days left • ${deadline}`,
        urgent: true,
      };
    }

    if (daysRemaining <= 7) {
      return {
        text:
          `🟠 ${daysRemaining} days left • ${deadline}`,
        urgent: true,
      };
    }

    return {
      text:
        `📅 ${daysRemaining} days left • ${deadline}`,
      urgent: false,
    };
  };

  // ==========================================================
  // RENDER CARD
  // ==========================================================

  const renderScholarship = ({
    item,
  }: {
    item: SavedScholarship;
  }) => {
    const deadlineInfo =
      getDeadlineText(
        item.deadline
      );

    const isApplied =
      item.status === "applied";

    return (
      <View style={styles.card}>

        {/* STATUS */}

        <View style={styles.topRow}>

          <View
            style={[
              styles.statusBadge,
              isApplied
                ? styles.appliedBadge
                : styles.savedBadge,
            ]}
          >
            <Text
              style={[
                styles.statusText,
                isApplied
                  ? styles.appliedText
                  : styles.savedText,
              ]}
            >
              {isApplied
                ? "✓ APPLIED"
                : "♥ SAVED"}
            </Text>
          </View>

        </View>

        {/* NAME */}

        <Text style={styles.name}>
          {item.scholarship_name}
        </Text>

        {/* DEADLINE */}

        <Text
          style={[
            styles.deadline,
            deadlineInfo.urgent &&
              styles.urgentDeadline,
          ]}
        >
          {deadlineInfo.text}
        </Text>

        {/* SAVED DATE */}

        <Text style={styles.savedDate}>
          Saved on{" "}
          {new Date(
            item.saved_at
          ).toLocaleDateString(
            "en-IN"
          )}
        </Text>

        {/* ACTIONS */}

        <View style={styles.actions}>

          {!isApplied && (
            <TouchableOpacity
              style={styles.applyButton}
              onPress={() =>
                markAsApplied(
                  item.scholarship_id
                )
              }
            >
              <Text
                style={
                  styles.applyButtonText
                }
              >
                Mark as Applied
              </Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={styles.removeButton}
            onPress={() =>
              removeScholarship(
                item.scholarship_id
              )
            }
          >
            <Text
              style={
                styles.removeButtonText
              }
            >
              Remove
            </Text>
          </TouchableOpacity>

        </View>

      </View>
    );
  };

  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {
    return (
      <View style={styles.center}>

        <ActivityIndicator
          size="large"
        />

        <Text style={styles.loadingText}>
          Loading your scholarships...
        </Text>

      </View>
    );
  }

  // ==========================================================
  // MAIN UI
  // ==========================================================

  return (
    <View style={styles.container}>

      {/* HEADER */}

      <View style={styles.header}>

        <Text style={styles.title}>
          My Scholarships
        </Text>

        <Text style={styles.subtitle}>
          Scholarships you want to keep track of
        </Text>

        <View style={styles.summary}>

          <View style={styles.summaryItem}>

            <Text
              style={
                styles.summaryNumber
              }
            >
              {scholarships.length}
            </Text>

            <Text
              style={
                styles.summaryLabel
              }
            >
              Saved
            </Text>

          </View>

          <View style={styles.summaryItem}>

            <Text
              style={
                styles.summaryNumber
              }
            >
              {
                scholarships.filter(
                  item =>
                    item.status ===
                    "applied"
                ).length
              }
            </Text>

            <Text
              style={
                styles.summaryLabel
              }
            >
              Applied
            </Text>

          </View>

        </View>

      </View>

      {/* ERROR */}

      {error ? (
        <View style={styles.center}>

          <Text style={styles.error}>
            {error}
          </Text>

        </View>

      ) : scholarships.length === 0 ? (

        <View style={styles.center}>

          <Text style={styles.emptyIcon}>
            ♡
          </Text>

          <Text style={styles.emptyTitle}>
            No saved scholarships
          </Text>

          <Text style={styles.emptyText}>
            Go to Matches and save scholarships
            {"\n"}
            you want to apply for.
          </Text>

        </View>

      ) : (

        <FlatList
          data={scholarships}
          keyExtractor={item =>
            String(item.id)
          }
          renderItem={
            renderScholarship
          }
          contentContainerStyle={
            styles.list
          }
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
            />
          }
          showsVerticalScrollIndicator={
            false
          }
        />

      )}

    </View>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({

  container: {
    flex: 1,
    backgroundColor: "#f5f6fa",
  },

  header: {
    paddingTop: 55,
    paddingHorizontal: 20,
    paddingBottom: 18,
    backgroundColor: "white",
  },

  title: {
    fontSize: 28,
    fontWeight: "bold",
  },

  subtitle: {
    marginTop: 5,
    fontSize: 15,
    color: "#666",
  },

  summary: {
    flexDirection: "row",
    marginTop: 18,
    gap: 10,
  },

  summaryItem: {
    flex: 1,
    backgroundColor: "#f5f6fa",
    borderRadius: 12,
    alignItems: "center",
    paddingVertical: 12,
  },

  summaryNumber: {
    fontSize: 21,
    fontWeight: "bold",
  },

  summaryLabel: {
    marginTop: 3,
    fontSize: 12,
    color: "#666",
  },

  list: {
    padding: 15,
    paddingBottom: 40,
  },

  card: {
    backgroundColor: "white",
    borderRadius: 16,
    padding: 18,
    marginBottom: 15,
    elevation: 3,
  },

  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
  },

  savedBadge: {
    backgroundColor: "#eef2ff",
  },

  appliedBadge: {
    backgroundColor: "#dff7e7",
  },

  statusText: {
    fontSize: 11,
    fontWeight: "bold",
  },

  savedText: {
    color: "#4f46e5",
  },

  appliedText: {
    color: "#15803d",
  },

  name: {
    fontSize: 19,
    fontWeight: "bold",
    marginTop: 12,
    marginBottom: 12,
  },

  deadline: {
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 7,
  },

  urgentDeadline: {
    color: "#dc2626",
  },

  savedDate: {
    fontSize: 12,
    color: "#888",
  },

  actions: {
    flexDirection: "row",
    gap: 10,
    marginTop: 16,
  },

  applyButton: {
    flex: 1,
    backgroundColor: "#4f46e5",
    paddingVertical: 11,
    borderRadius: 10,
    alignItems: "center",
  },

  applyButtonText: {
    color: "white",
    fontWeight: "bold",
    fontSize: 13,
  },

  removeButton: {
    paddingHorizontal: 18,
    paddingVertical: 11,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#ddd",
    alignItems: "center",
  },

  removeButtonText: {
    color: "#555",
    fontWeight: "600",
    fontSize: 13,
  },

  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 25,
  },

  loadingText: {
    marginTop: 12,
    fontSize: 15,
  },

  error: {
    color: "red",
    textAlign: "center",
    fontSize: 15,
  },

  emptyIcon: {
    fontSize: 48,
    color: "#4f46e5",
  },

  emptyTitle: {
    marginTop: 10,
    fontSize: 20,
    fontWeight: "bold",
  },

  emptyText: {
    marginTop: 8,
    color: "#666",
    textAlign: "center",
    lineHeight: 20,
  },

});
