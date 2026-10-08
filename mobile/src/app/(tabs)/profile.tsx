import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { router } from "expo-router";

import {
  authenticatedFetch,
  clearAuthData,
  getAccessToken,
  getStoredUser,
} from "../../services/authService";

const API_URL = "http://10.43.36.85:8000";

export default function ProfileScreen() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  const [educationLevel, setEducationLevel] = useState("");
  const [course, setCourse] = useState("");
  const [category, setCategory] = useState("");
  const [gender, setGender] = useState("");
  const [state, setState] = useState("");
  const [year, setYear] = useState("");
  const [familyIncome, setFamilyIncome] = useState("");
  const [marks, setMarks] = useState("");

  const [accessToken, setAccessToken] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [loggingOut, setLoggingOut] = useState(false);

  const [showDetails, setShowDetails] = useState(false);
  const [editMode, setEditMode] = useState(false);

  // ==========================================================
  // LOAD LOGGED-IN USER + PROFILE
  // ==========================================================

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoadingProfile(true);

      const user = await getStoredUser();
      const token = await getAccessToken();

      if (!user || !token) {
        await clearAuthData();

        Alert.alert(
          "Session Expired",
          "Please login again."
        );

        router.replace("/login");
        return;
      }

      const userEmail = user.email;

      setEmail(userEmail);
      setAccessToken(token);

      const response = await authenticatedFetch(
        `${API_URL}/profile/${encodeURIComponent(userEmail)}`,
        {
          method: "GET",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to load profile"
        );
      }

      setName(data.name ?? "");
      setEducationLevel(data.education_level ?? "");
      setCourse(data.course ?? "");
      setCategory(data.category ?? "");
      setGender(data.gender ?? "");
      setState(data.state ?? "");
      setYear(data.year ?? "");

      if (
        data.family_income !== null &&
        data.family_income !== undefined
      ) {
        setFamilyIncome(String(data.family_income));
      } else {
        setFamilyIncome("");
      }

      if (
        data.marks !== null &&
        data.marks !== undefined
      ) {
        setMarks(String(data.marks));
      } else {
        setMarks("");
      }

    } catch (error) {
      console.log("Profile load error:", error);

      if (
        error instanceof Error &&
        error.message === "SESSION_EXPIRED"
      ) {
        await clearAuthData();

        Alert.alert(
          "Session Expired",
          "Please login again."
        );

        router.replace("/login");
        return;
      }

      Alert.alert(
        "Error",
        "Could not load your profile. Make sure the backend is running."
      );
    } finally {
      setLoadingProfile(false);
    }
  };

  // ==========================================================
  // SAVE / UPDATE PROFILE
  // ==========================================================

  const saveProfile = async () => {
    if (!name.trim()) {
      Alert.alert(
        "Missing Information",
        "Please enter your name."
      );
      return;
    }

    if (!email.trim()) {
      Alert.alert(
        "Missing Information",
        "Please enter your email."
      );
      return;
    }

    try {
      setLoading(true);

      let token = accessToken;

      if (!token) {
        token = await getAccessToken();
        setAccessToken(token);
      }

      if (!token) {
        await clearAuthData();

        Alert.alert(
          "Session Expired",
          "Please login again."
        );

        router.replace("/login");
        return;
      }

      const response = await authenticatedFetch(
        `${API_URL}/profile`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: name.trim(),
            email: email.trim(),
            education_level:
              educationLevel.trim() || null,
            course:
              course.trim() || null,
            category:
              category.trim() || null,
            gender:
              gender.trim() || null,
            state:
              state.trim() || null,
            year:
              year.trim() || null,
            family_income:
              familyIncome.trim() === ""
                ? null
                : Number(familyIncome),
            marks:
              marks.trim() === ""
                ? null
                : Number(marks),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to save profile"
        );
      }

      Alert.alert(
        "Success",
        "Your details have been updated successfully."
      );

      setEditMode(false);
      setShowDetails(true);

    } catch (error) {
      console.log("Profile save error:", error);

      if (
        error instanceof Error &&
        error.message === "SESSION_EXPIRED"
      ) {
        await clearAuthData();

        Alert.alert(
          "Session Expired",
          "Please login again."
        );

        router.replace("/login");
        return;
      }

      Alert.alert(
        "Error",
        "Could not update your details. Make sure the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  // ==========================================================
  // LOGOUT
  // ==========================================================

  const handleLogout = () => {
    Alert.alert(
      "Logout",
      "Are you sure you want to logout?",
      [
        {
          text: "Cancel",
          style: "cancel",
        },
        {
          text: "Logout",
          style: "destructive",
          onPress: performLogout,
        },
      ]
    );
  };

  const performLogout = async () => {
    try {
      setLoggingOut(true);

      await clearAuthData();

      setAccessToken(null);

      router.replace("/login");

    } catch (error) {
      console.log(
        "Logout error:",
        error
      );

      Alert.alert(
        "Logout Failed",
        "Could not logout. Please try again."
      );
    } finally {
      setLoggingOut(false);
    }
  };

  // ==========================================================
  // DETAIL ROW
  // ==========================================================

  const DetailRow = ({
    label,
    value,
  }: {
    label: string;
    value: string;
  }) => {
    return (
      <View style={styles.detailRow}>
        <Text style={styles.detailLabel}>
          {label}
        </Text>

        <Text style={styles.detailValue}>
          {value || "Not provided"}
        </Text>
      </View>
    );
  };

  // ==========================================================
  // LOADING
  // ==========================================================

  if (loadingProfile) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator
          size="large"
          color="#4f46e5"
        />

        <Text style={styles.loadingText}>
          Loading your profile...
        </Text>
      </View>
    );
  }

  // ==========================================================
  // MAIN PROFILE
  // ==========================================================

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      <Text style={styles.title}>
        Profile
      </Text>

      <Text style={styles.subtitle}>
        Manage your ScholarAI profile
      </Text>

      {!showDetails && !editMode && (
        <>
          <View style={styles.profileCard}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {name
                  ? name.charAt(0).toUpperCase()
                  : "S"}
              </Text>
            </View>

            <Text style={styles.profileName}>
              {name || "Student"}
            </Text>

            <Text style={styles.profileEmail}>
              {email}
            </Text>

            <Text style={styles.profileCourse}>
              {course || "Course not added"}
            </Text>
          </View>

          <TouchableOpacity
            style={styles.primaryButton}
            onPress={() => setShowDetails(true)}
          >
            <Text style={styles.primaryButtonText}>
              My Details
            </Text>
          </TouchableOpacity>
        </>
      )}

      {/* ======================================================
          MY DETAILS
      ====================================================== */}

      {showDetails && !editMode && (
        <>
          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>
              My Details
            </Text>

            <DetailRow
              label="Name"
              value={name}
            />

            <DetailRow
              label="Email"
              value={email}
            />

            <DetailRow
              label="Education"
              value={educationLevel}
            />

            <DetailRow
              label="Course"
              value={course}
            />

            <DetailRow
              label="Category"
              value={category}
            />

            <DetailRow
              label="Gender"
              value={gender}
            />

            <DetailRow
              label="State"
              value={state}
            />

            <DetailRow
              label="Year"
              value={year}
            />

            <DetailRow
              label="Marks"
              value={
                marks
                  ? `${marks}%`
                  : ""
              }
            />

            <DetailRow
              label="Family Income"
              value={
                familyIncome
                  ? `₹${Number(
                      familyIncome
                    ).toLocaleString("en-IN")}`
                  : ""
              }
            />
          </View>

          <TouchableOpacity
            style={styles.primaryButton}
            onPress={() => setEditMode(true)}
          >
            <Text style={styles.primaryButtonText}>
              Update Details
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => setShowDetails(false)}
          >
            <Text style={styles.secondaryButtonText}>
              Back to Profile
            </Text>
          </TouchableOpacity>
        </>
      )}

      {/* ======================================================
          UPDATE DETAILS
      ====================================================== */}

      {editMode && (
        <View style={styles.formCard}>
          <Text style={styles.sectionTitle}>
            Update Details
          </Text>

          <Text style={styles.label}>
            Name
          </Text>

          <TextInput
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Enter your name"
          />

          <Text style={styles.label}>
            Email
          </Text>

          <TextInput
            style={[
              styles.input,
              styles.disabledInput,
            ]}
            value={email}
            editable={false}
            autoCapitalize="none"
          />

          <Text style={styles.emailNote}>
            Email is currently used as your profile identifier.
          </Text>

          <Text style={styles.label}>
            Education Level
          </Text>

          <TextInput
            style={styles.input}
            value={educationLevel}
            onChangeText={setEducationLevel}
            placeholder="Example: UG"
          />

          <Text style={styles.label}>
            Course
          </Text>

          <TextInput
            style={styles.input}
            value={course}
            onChangeText={setCourse}
            placeholder="Example: B.E Computer Science"
          />

          <Text style={styles.label}>
            Category
          </Text>

          <TextInput
            style={styles.input}
            value={category}
            onChangeText={setCategory}
            placeholder="Example: General"
          />

          <Text style={styles.label}>
            Gender
          </Text>

          <TextInput
            style={styles.input}
            value={gender}
            onChangeText={setGender}
            placeholder="Example: Female"
          />

          <Text style={styles.label}>
            State
          </Text>

          <TextInput
            style={styles.input}
            value={state}
            onChangeText={setState}
            placeholder="Example: Tamil Nadu"
          />

          <Text style={styles.label}>
            Year
          </Text>

          <TextInput
            style={styles.input}
            value={year}
            onChangeText={setYear}
            placeholder="Example: 2nd Year"
          />

          <Text style={styles.label}>
            Marks
          </Text>

          <TextInput
            style={styles.input}
            value={marks}
            onChangeText={setMarks}
            placeholder="Example: 82"
            keyboardType="numeric"
          />

          <Text style={styles.label}>
            Family Income
          </Text>

          <TextInput
            style={styles.input}
            value={familyIncome}
            onChangeText={setFamilyIncome}
            placeholder="Example: 400000"
            keyboardType="numeric"
          />

          <TouchableOpacity
            style={styles.primaryButton}
            onPress={saveProfile}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.primaryButtonText}>
                Save Changes
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => setEditMode(false)}
            disabled={loading}
          >
            <Text style={styles.secondaryButtonText}>
              Cancel
            </Text>
          </TouchableOpacity>
        </View>
      )}

      {/* ======================================================
          LOGOUT
      ====================================================== */}

      {!editMode && (
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={handleLogout}
          disabled={loggingOut}
        >
          {loggingOut ? (
            <ActivityIndicator color="#dc2626" />
          ) : (
            <Text style={styles.logoutButtonText}>
              Logout
            </Text>
          )}
        </TouchableOpacity>
      )}
    </ScrollView>
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

  content: {
    padding: 20,
    paddingTop: 60,
    paddingBottom: 50,
  },

  title: {
    fontSize: 30,
    fontWeight: "800",
    color: "#171717",
  },

  subtitle: {
    fontSize: 15,
    color: "#666",
    marginTop: 5,
    marginBottom: 25,
  },

  profileCard: {
    backgroundColor: "white",
    borderRadius: 18,
    padding: 25,
    alignItems: "center",
    elevation: 3,
  },

  avatar: {
    width: 78,
    height: 78,
    borderRadius: 39,
    backgroundColor: "#4f46e5",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 14,
  },

  avatarText: {
    color: "white",
    fontSize: 32,
    fontWeight: "800",
  },

  profileName: {
    fontSize: 22,
    fontWeight: "800",
  },

  profileEmail: {
    fontSize: 14,
    color: "#666",
    marginTop: 5,
  },

  profileCourse: {
    fontSize: 14,
    color: "#4f46e5",
    fontWeight: "600",
    marginTop: 8,
  },

  sectionCard: {
    backgroundColor: "white",
    borderRadius: 18,
    padding: 20,
    elevation: 3,
  },

  formCard: {
    backgroundColor: "white",
    borderRadius: 18,
    padding: 20,
    elevation: 3,
  },

  sectionTitle: {
    fontSize: 21,
    fontWeight: "800",
    marginBottom: 15,
  },

  detailRow: {
    paddingVertical: 13,
    borderBottomWidth: 1,
    borderBottomColor: "#eeeeee",
  },

  detailLabel: {
    fontSize: 12,
    color: "#777",
    marginBottom: 4,
  },

  detailValue: {
    fontSize: 15,
    fontWeight: "600",
    color: "#222",
  },

  label: {
    fontSize: 14,
    fontWeight: "600",
    marginTop: 13,
    marginBottom: 6,
  },

  input: {
    backgroundColor: "#fafafa",
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
  },

  disabledInput: {
    backgroundColor: "#eeeeee",
    color: "#777",
  },

  emailNote: {
    fontSize: 11,
    color: "#888",
    marginTop: 5,
  },

  primaryButton: {
    backgroundColor: "#4f46e5",
    paddingVertical: 15,
    borderRadius: 12,
    marginTop: 22,
    alignItems: "center",
  },

  primaryButtonText: {
    color: "white",
    fontSize: 16,
    fontWeight: "700",
  },

  secondaryButton: {
    backgroundColor: "white",
    borderWidth: 1,
    borderColor: "#d1d5db",
    paddingVertical: 14,
    borderRadius: 12,
    marginTop: 10,
    alignItems: "center",
  },

  secondaryButtonText: {
    color: "#444",
    fontSize: 15,
    fontWeight: "600",
  },

  logoutButton: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#fecaca",
    paddingVertical: 15,
    borderRadius: 12,
    marginTop: 30,
    alignItems: "center",
  },

  logoutButtonText: {
    color: "#dc2626",
    fontSize: 16,
    fontWeight: "700",
  },

  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f5f6fa",
  },

  loadingText: {
    marginTop: 12,
    color: "#666",
  },
});
