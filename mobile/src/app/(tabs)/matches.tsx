import React, { useEffect, useState } from "react";

import {
  ActivityIndicator,
  Alert,
  FlatList,
  Linking,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import {
  cancelScholarshipNotifications,
  scheduleScholarshipDeadlineNotifications,
} from "../../services/notificationService";

import {
  getAccessToken,
  getStoredUser,
  authenticatedFetch,
} from "../../services/authService";

// ============================================================
// BACKEND
// ============================================================

const API_URL = "http://10.43.36.85:8000";

// ============================================================
// TYPES
// ============================================================

type Scholarship = {
  id: string;
  name: string;

  education_level: string | string[] | null;
  level?: string;
  class_range?: string;

  category: string[] | null;

  income_limit: number | null;
  income_max?: number | null;

  minimum_marks: number | null;
  marks_min?: number | null;

  benefit: string | null;

  documents: string[] | null;

  application_url: string | null;
  how_to_apply?: string | null;

  deadline: string | null;

  source: string | null;
  source_url: string | null;

  eligibility: string | null;
  notes?: string | null;

  status: "eligible" | "needs_verification";

  match_score: number;
  match_reason: string;

  checks: string[];
  verification_reasons: string[];
};

type SavedScholarship = {
  scholarship_id: string;
  scholarship_name: string;
  deadline: string | null;
  status: string;
};

// ============================================================
// SCREEN
// ============================================================

export default function MatchesScreen() {
  const [scholarships, setScholarships] =
    useState<Scholarship[]>([]);

  const [savedScholarships, setSavedScholarships] =
    useState<Set<string>>(new Set());

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState("");

  const [savingId, setSavingId] =
    useState<string | null>(null);

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
  // FETCH MATCHES
  // ==========================================================

  const fetchMatches = async (
    userEmail?: string,
    token?: string
  ) => {
    try {
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

      // authenticatedFetch automatically refreshes
      // the access token if it has expired.
      const response = await authenticatedFetch(
        `${API_URL}/matches/${encodeURIComponent(
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
            "You are not authorized to access these matches."
          );
        }

        throw new Error(
          `Server error: ${response.status}`
        );
      }

      const data = await response.json();

      setScholarships(data.matches || []);
    } catch (err) {
      console.log(
        "Match request failed:",
        err
      );

      setError(
        err instanceof Error
          ? err.message
          : "Could not load scholarships. Make sure the backend is running."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // ==========================================================
  // FETCH SAVED SCHOLARSHIPS
  // ==========================================================

  const fetchSavedScholarships = async (
    userEmail?: string,
    token?: string
  ) => {
    try {
      const currentEmail =
        userEmail || email;

      const currentToken =
        token || accessToken;

      if (!currentEmail || !currentToken) {
        return;
      }

      // Automatic token refresh happens here too.
      const response = await authenticatedFetch(
        `${API_URL}/saved/${encodeURIComponent(
          currentEmail
        )}`
      );

      if (!response.ok) {
        if (response.status === 401) {
          console.log(
            "Saved request: session expired."
          );
        }

        return;
      }

      const data = await response.json();

      const savedIds = new Set<string>();

      (data.saved || []).forEach(
        (item: SavedScholarship) => {
          savedIds.add(item.scholarship_id);
        }
      );

      setSavedScholarships(savedIds);
    } catch (err) {
      console.log(
        "Saved scholarship request failed:",
        err
      );
    }
  };

  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {
    const loadUserAndData = async () => {
      try {
        const auth = await loadAuthData();

        await Promise.all([
          fetchMatches(
            auth.email,
            auth.token
          ),
          fetchSavedScholarships(
            auth.email,
            auth.token
          ),
        ]);
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

    loadUserAndData();
  }, []);

  // ==========================================================
  // REFRESH
  // ==========================================================

  const onRefresh = async () => {
    setRefreshing(true);

    try {
      const auth = await loadAuthData();

      await Promise.all([
        fetchMatches(
          auth.email,
          auth.token
        ),
        fetchSavedScholarships(
          auth.email,
          auth.token
        ),
      ]);
    } catch (err) {
      console.log(
        "Refresh failed:",
        err
      );

      setRefreshing(false);
    }
  };

  // ==========================================================
  // SAVE / UNSAVE SCHOLARSHIP
  // ==========================================================

  const saveScholarship = async (
    item: Scholarship
  ) => {
    try {
      setSavingId(item.id);

      const alreadySaved =
        savedScholarships.has(item.id);

      const currentEmail = email;
      const currentToken = accessToken;

      if (!currentEmail || !currentToken) {
        Alert.alert(
          "Login Required",
          "Please login again."
        );
        return;
      }

      // ======================================================
      // UNSAVE
      // ======================================================

      if (alreadySaved) {
        const response = await authenticatedFetch(
          `${API_URL}/saved/${encodeURIComponent(
            currentEmail
          )}/${encodeURIComponent(item.id)}`,
          {
            method: "DELETE",
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error(
              "Your session has expired."
            );
          }

          if (response.status === 403) {
            throw new Error(
              "You are not authorized to remove this scholarship."
            );
          }

          throw new Error(
            "Failed to remove scholarship"
          );
        }

        // Cancel deadline notifications
        try {
          await cancelScholarshipNotifications(
            item.id
          );
        } catch (notificationError) {
          console.log(
            "Notification cancellation failed:",
            notificationError
          );
        }

        setSavedScholarships(previous => {
          const updated = new Set(previous);

          updated.delete(item.id);

          return updated;
        });

        return;
      }

      // ======================================================
      // SAVE
      // ======================================================

      const response = await authenticatedFetch(
        `${API_URL}/saved/${encodeURIComponent(
          currentEmail
        )}`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            scholarship_id: item.id,
            scholarship_name: item.name,
            deadline: item.deadline,
          }),
        }
      );

      if (!response.ok) {
        let data: any = {};

        try {
          data = await response.json();
        } catch {
          // Ignore JSON parsing failure
        }

        throw new Error(
          data.detail ||
            "Failed to save scholarship"
        );
      }

      // ======================================================
      // SCHEDULE DEADLINE NOTIFICATIONS
      // ======================================================

      try {
        const scheduledCount =
          await scheduleScholarshipDeadlineNotifications(
            item.id,
            item.name,
            item.deadline
          );

        console.log(
          `Scheduled ${scheduledCount} notifications for ${item.name}`
        );
      } catch (notificationError) {
        console.log(
          "Notification scheduling failed:",
          notificationError
        );
      }

      // ======================================================
      // UPDATE UI
      // ======================================================

      setSavedScholarships(previous => {
        const updated = new Set(previous);

        updated.add(item.id);

        return updated;
      });
    } catch (err) {
      console.log(
        "Save scholarship error:",
        err
      );

      Alert.alert(
        "Error",
        err instanceof Error
          ? err.message
          : "Could not update saved scholarship."
      );
    } finally {
      setSavingId(null);
    }
  };

  // ==========================================================
  // APPLY NOW
  // ==========================================================

  const handleApply = async (
    applicationUrl: string | null
  ) => {
    if (!applicationUrl) {
      Alert.alert(
        "Application Link Unavailable",
        "The official application link is not available for this scholarship."
      );

      return;
    }

    try {
      const supported =
        await Linking.canOpenURL(
          applicationUrl
        );

      if (!supported) {
        Alert.alert(
          "Unable to Open Link",
          "The application website could not be opened."
        );

        return;
      }

      await Linking.openURL(
        applicationUrl
      );
    } catch (error) {
      console.log(
        "Apply link error:",
        error
      );

      Alert.alert(
        "Error",
        "Could not open the official application website."
      );
    }
  };

  // ==========================================================
  // DEADLINE HELPER
  // ==========================================================

  const getDeadlineInfo = (
    deadline: string | null
  ) => {
    if (!deadline) {
      return {
        text:
          "Deadline: Check official portal",
        urgent: false,
      };
    }

    let deadlineDate: Date | null = null;

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

    const daysRemaining = Math.ceil(
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
  // RENDER SCHOLARSHIP
  // ==========================================================

  const renderScholarship = ({
    item,
  }: {
    item: Scholarship;
  }) => {
    const isEligible =
      item.status === "eligible";

    const isSaved =
      savedScholarships.has(item.id);

    const deadlineInfo =
      getDeadlineInfo(item.deadline);

    return (
      <View style={styles.card}>

        {/* TOP ROW */}

        <View style={styles.topRow}>

          <View
            style={[
              styles.statusBadge,
              isEligible
                ? styles.eligibleBadge
                : styles.verifyBadge,
            ]}
          >
            <Text style={styles.statusText}>
              {isEligible
                ? "✓ ELIGIBLE"
                : "⚠ VERIFY"}
            </Text>
          </View>

          <Text style={styles.score}>
            {item.match_score}%
          </Text>

        </View>

        {/* NAME */}

        <Text style={styles.name}>
          {item.name}
        </Text>

        {/* MATCH LABEL */}

        <Text
          style={
            isEligible
              ? styles.matchLabel
              : styles.verifyLabel
          }
        >
          {isEligible
            ? "You appear eligible based on your profile"
            : "Some eligibility details need verification"}
        </Text>

        {/* LEVEL */}

        {(item.class_range ||
          item.level ||
          item.education_level) && (
          <Text style={styles.info}>
            🎓 Level:{" "}
            {item.class_range ||
              item.level ||
              (Array.isArray(
                item.education_level
              )
                ? item.education_level.join(
                    ", "
                  )
                : item.education_level)}
          </Text>
        )}

        {/* BENEFIT */}

        {item.benefit && (
          <Text style={styles.info}>
            💰 Benefit: {item.benefit}
          </Text>
        )}

        {/* INCOME */}

        {item.income_limit !== null &&
          item.income_limit !== undefined && (
            <Text style={styles.info}>
              💵 Income limit: ₹
              {item.income_limit.toLocaleString(
                "en-IN"
              )}
            </Text>
          )}

        {/* MARKS */}

        {item.minimum_marks !== null &&
          item.minimum_marks !== undefined && (
            <Text style={styles.info}>
              📊 Minimum marks:{" "}
              {item.minimum_marks}%
            </Text>
          )}

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

        {/* SAVE BUTTON */}

        <TouchableOpacity
          style={[
            styles.saveButton,
            isSaved &&
              styles.savedButton,
          ]}
          onPress={() =>
            saveScholarship(item)
          }
          disabled={
            savingId === item.id
          }
        >
          {savingId === item.id ? (
            <ActivityIndicator
              size="small"
              color={
                isSaved
                  ? "#4f46e5"
                  : "white"
              }
            />
          ) : (
            <Text
              style={[
                styles.saveButtonText,
                isSaved &&
                  styles.savedButtonText,
              ]}
            >
              {isSaved
                ? "♥ Saved"
                : "♡ Save Scholarship"}
            </Text>
          )}
        </TouchableOpacity>

        {/* MATCH REASON */}

        <View style={styles.reasonBox}>

          <Text style={styles.reasonTitle}>
            {isEligible
              ? "Why you match"
              : "What needs verification"}
          </Text>

          {item.checks &&
            item.checks.length > 0 && (
              <View style={styles.reasonSection}>
                {item.checks.map(
                  (check, index) => (
                    <Text
                      key={`check-${index}`}
                      style={
                        styles.checkItem
                      }
                    >
                      ✓ {check}
                    </Text>
                  )
                )}
              </View>
            )}

          {item.verification_reasons &&
            item.verification_reasons.length >
              0 && (
              <View style={styles.reasonSection}>
                {item.verification_reasons.map(
                  (reason, index) => (
                    <Text
                      key={`verify-${index}`}
                      style={
                        styles.verifyItem
                      }
                    >
                      ⚠ {reason}
                    </Text>
                  )
                )}
              </View>
            )}

        </View>

        {/* ELIGIBILITY */}

        {item.eligibility && (
          <View style={styles.detailsBox}>

            <Text
              style={styles.documentsTitle}
            >
              Eligibility
            </Text>

            <Text
              style={styles.detailsText}
            >
              {item.eligibility}
            </Text>

          </View>
        )}

        {/* DOCUMENTS */}

        {item.documents &&
          item.documents.length > 0 && (
            <View style={styles.documentsBox}>

              <Text
                style={styles.documentsTitle}
              >
                📄 Documents
              </Text>

              {item.documents.map(
                (document, index) => (
                  <Text
                    key={index}
                    style={styles.document}
                  >
                    • {document}
                  </Text>
                )
              )}

            </View>
          )}

        {/* APPLY NOW */}

        {item.application_url && (
          <TouchableOpacity
            style={styles.applyButton}
            onPress={() =>
              handleApply(
                item.application_url
              )
            }
          >
            <Text
              style={styles.applyButtonText}
            >
              Apply Now
            </Text>
          </TouchableOpacity>
        )}

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
          Finding scholarships for you...
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
          My Matches
        </Text>

        <Text style={styles.subtitle}>
          Scholarships personalized for your profile
        </Text>

        <View style={styles.summaryRow}>

          <View style={styles.summaryBox}>
            <Text style={styles.summaryNumber}>
              {
                scholarships.filter(
                  item =>
                    item.status ===
                    "eligible"
                ).length
              }
            </Text>

            <Text style={styles.summaryLabel}>
              Eligible
            </Text>
          </View>

          <View style={styles.summaryBox}>
            <Text style={styles.summaryNumber}>
              {
                scholarships.filter(
                  item =>
                    item.status ===
                    "needs_verification"
                ).length
              }
            </Text>

            <Text style={styles.summaryLabel}>
              Verify
            </Text>
          </View>

          <View style={styles.summaryBox}>
            <Text style={styles.summaryNumber}>
              {savedScholarships.size}
            </Text>

            <Text style={styles.summaryLabel}>
              Saved
            </Text>
          </View>

        </View>

      </View>

      {/* ERROR */}

      {error !== "" ? (
        <View style={styles.center}>

          <Text style={styles.error}>
            {error}
          </Text>

        </View>
      ) : scholarships.length === 0 ? (
        <View style={styles.center}>

          <Text style={styles.emptyTitle}>
            No scholarships found
          </Text>

          <Text style={styles.emptyText}>
            Try updating your profile with
            {"\n"}
            more details.
          </Text>

        </View>
      ) : (
        <FlatList
          data={scholarships}
          keyExtractor={item => item.id}
          renderItem={renderScholarship}
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

  summaryRow: {
    flexDirection: "row",
    marginTop: 18,
    gap: 10,
  },

  summaryBox: {
    flex: 1,
    backgroundColor: "#f5f6fa",
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },

  summaryNumber: {
    fontSize: 20,
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
    alignItems: "center",
  },

  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
  },

  eligibleBadge: {
    backgroundColor: "#dff7e7",
  },

  verifyBadge: {
    backgroundColor: "#fff1cc",
  },

  statusText: {
    fontSize: 11,
    fontWeight: "bold",
  },

  score: {
    fontSize: 18,
    fontWeight: "bold",
  },

  name: {
    fontSize: 19,
    fontWeight: "bold",
    marginTop: 12,
    marginBottom: 7,
  },

  matchLabel: {
    color: "#15803d",
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 12,
  },

  verifyLabel: {
    color: "#a16207",
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 12,
  },

  info: {
    fontSize: 14,
    marginBottom: 7,
    color: "#444",
  },

  deadline: {
    fontSize: 14,
    fontWeight: "600",
    marginTop: 5,
    marginBottom: 12,
  },

  urgentDeadline: {
    color: "#dc2626",
  },

  saveButton: {
    backgroundColor: "#4f46e5",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 5,
    marginBottom: 12,
  },

  savedButton: {
    backgroundColor: "#eef2ff",
    borderWidth: 1,
    borderColor: "#4f46e5",
  },

  saveButtonText: {
    color: "white",
    fontSize: 14,
    fontWeight: "bold",
  },

  savedButtonText: {
    color: "#4f46e5",
  },

  // ==========================================================
  // APPLY NOW BUTTON
  // ==========================================================

  applyButton: {
    backgroundColor: "#16a34a",
    paddingVertical: 13,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },

  applyButtonText: {
    color: "white",
    fontSize: 15,
    fontWeight: "700",
  },

  // ==========================================================
  // MATCH REASON
  // ==========================================================

  reasonBox: {
    backgroundColor: "#f1f3f8",
    padding: 12,
    borderRadius: 10,
    marginTop: 3,
  },

  reasonTitle: {
    fontSize: 13,
    fontWeight: "bold",
    marginBottom: 7,
  },

  reasonSection: {
    marginTop: 2,
  },

  checkItem: {
    fontSize: 13,
    color: "#166534",
    marginBottom: 4,
  },

  verifyItem: {
    fontSize: 13,
    color: "#92400e",
    marginBottom: 4,
  },

  detailsBox: {
    marginTop: 12,
    backgroundColor: "#fafafa",
    padding: 12,
    borderRadius: 10,
  },

  detailsText: {
    fontSize: 13,
    color: "#555",
    lineHeight: 19,
  },

  documentsBox: {
    marginTop: 12,
  },

  documentsTitle: {
    fontSize: 14,
    fontWeight: "bold",
    marginBottom: 5,
  },

  document: {
    fontSize: 13,
    color: "#555",
    marginBottom: 3,
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
    textAlign: "center",
    color: "red",
    fontSize: 15,
  },

  emptyTitle: {
    fontSize: 20,
    fontWeight: "bold",
  },

  emptyText: {
    marginTop: 8,
    color: "#666",
    textAlign: "center",
  },

});
