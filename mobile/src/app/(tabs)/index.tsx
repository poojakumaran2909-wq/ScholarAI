import { useEffect, useState } from "react";

import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import {
  AudioModule,
  RecordingPresets,
  useAudioRecorder,
  createAudioPlayer,
} from "expo-audio";

// ======================================================
// BACKEND CONFIGURATION
// ======================================================

const API_URL = "http://10.43.36.85:8000";

// ======================================================
// TYPES
// ======================================================

type Scholarship = {
  id?: string;
  name?: string;
  level?: string;
  category?: string | string[];
  class_range?: string;
  income_max?: number | null;
  marks_min?: number | null;
  benefit?: string;
  documents?: string[];
  how_to_apply?: string;
  deadline?: string;
  source?: string;
  notes?: string;
};

// ======================================================
// HOME SCREEN
// ======================================================

export default function HomeScreen() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [scholarships, setScholarships] = useState<Scholarship[]>([]);

  const [loading, setLoading] = useState(false);

  const [recording, setRecording] = useState(false);
  const [audioUri, setAudioUri] = useState<string | null>(null);
  const [permissionDenied, setPermissionDenied] = useState(false);

  // ====================================================
  // AUDIO RECORDER
  // ====================================================

  const audioRecorder = useAudioRecorder(
    RecordingPresets.HIGH_QUALITY
  );

  // ====================================================
  // REQUEST MICROPHONE PERMISSION
  // ====================================================

  useEffect(() => {
    const requestMicrophonePermission = async () => {
      try {
        const result =
          await AudioModule.requestRecordingPermissionsAsync();

        if (!result.granted) {
          setPermissionDenied(true);

          Alert.alert(
            "Microphone Permission",
            "Please allow microphone access to use voice questions."
          );
        }
      } catch (error) {
        console.error(
          "Microphone permission error:",
          error
        );

        setPermissionDenied(true);
      }
    };

    requestMicrophonePermission();
  }, []);

  const speakAnswer = async (text: string) => {
  try {
    if (!text.trim()) return;

    console.log("🔊 Generating speech...");

    const response = await fetch(`${API_URL}/speak`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text.trim(),
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("TTS backend error:", errorText);
      return;
    }

    const audioBlob = await response.blob();

    const audioUrl = URL.createObjectURL(audioBlob);

    const player = createAudioPlayer(audioUrl);

    player.play();

    console.log("🔊 Playing AI answer");

    }catch (error) {
    console.error("TTS playback error:", error);
    }
  };


  // ====================================================
  // ASK SCHOLARSHIP
  // ====================================================

  const askScholarship = async (
    voiceQuestion?: string
  ) => {
    const trimmedQuestion =
      (voiceQuestion ?? question).trim();

    if (!trimmedQuestion) {
      Alert.alert(
        "Question required",
        "Please enter a scholarship question."
      );

      return;
    }

    setQuestion(trimmedQuestion);

    setLoading(true);
    setAnswer("");
    setScholarships([]);

    try {
      console.log(
        "Sending question:",
        trimmedQuestion
      );

      const response = await fetch(
        `${API_URL}/ask`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            question: trimmedQuestion,
          }),
        }
      );

      if (!response.ok) {
        const errorText =
          await response.text();

        console.error(
          "Backend error:",
          errorText
        );

        throw new Error(
          `Server returned ${response.status}`
        );
      }

      const data = await response.json();

      console.log(
        "Backend response:",
        data
      );

      const aiAnswer =
        data.answer ||
        "No answer was generated.";

      setAnswer(aiAnswer);

      await speakAnswer(aiAnswer);

      setScholarships(
        Array.isArray(data.scholarships)
          ? data.scholarships
          : []
      );

    } catch (error) {
      console.error(
        "Scholarship request failed:",
        error
      );

      setAnswer(
        "Unable to connect to the scholarship server."
      );

      Alert.alert(
        "Connection Error",
        "Make sure FastAPI is running and your phone and computer are connected to the same Wi-Fi network."
      );

    } finally {
      setLoading(false);
    }
  };

  // ====================================================
  // TRANSCRIBE AUDIO
  // ====================================================

  const transcribeAudio = async (
    uri: string
  ) => {
    try {
      console.log(
        "Uploading audio:",
        uri
      );

      const formData = new FormData();

      formData.append(
        "file",
        {
          uri: uri,
          name: "voice-question.m4a",
          type: "audio/m4a",
        } as any
      );

      console.log(
        "Sending audio to:",
        `${API_URL}/transcribe`
      );

      const response = await fetch(
        `${API_URL}/transcribe`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const errorText =
          await response.text();

        console.error(
          "Transcription backend error:",
          errorText
        );

        throw new Error(
          `Transcription failed: ${response.status}`
        );
      }

      const data =
        await response.json();

      console.log(
        "Transcription response:",
        data
      );

      const text =
        typeof data.text === "string"
          ? data.text.trim()
          : "";

      if (!text) {
        throw new Error(
          "No speech was detected."
        );
      }

      // ----------------------------------------------
      // Put spoken question into text box
      // ----------------------------------------------

      setQuestion(text);

      console.log(
        "🎤 Transcribed question:",
        text
      );

      // ----------------------------------------------
      // Automatically ask the AI
      // ----------------------------------------------

      await askScholarship(text);

    } catch (error) {
      console.error(
        "Transcription error:",
        error
      );

      Alert.alert(
        "Voice Error",
        "I could not understand your question. Please try speaking again."
      );
    }
  };

  // ====================================================
  // START RECORDING
  // ====================================================

  const startRecording = async () => {
    if (permissionDenied) {
      Alert.alert(
        "Microphone permission required",
        "Please allow microphone access in your phone settings."
      );

      return;
    }

    try {
      setAudioUri(null);

      await audioRecorder.prepareToRecordAsync();

      audioRecorder.record();

      setRecording(true);

      console.log(
        "🎤 Recording started"
      );

    } catch (error) {
      console.error(
        "Start recording error:",
        error
      );

      Alert.alert(
        "Recording Error",
        "Could not start recording."
      );
    }
  };

  // ====================================================
  // STOP RECORDING
  // ====================================================

  const stopRecording = async () => {
    try {
      console.log(
        "⏹ Stopping recording..."
      );

      await audioRecorder.stop();

      setRecording(false);

      const uri =
        audioRecorder.uri;

      if (!uri) {
        console.error(
          "No audio URI returned."
        );

        Alert.alert(
          "Recording Error",
          "No audio recording was created."
        );

        return;
      }

      setAudioUri(uri);

      console.log(
        "✅ Recording completed:",
        uri
      );

      // ----------------------------------------------
      // Send recording to backend
      // ----------------------------------------------

      setLoading(true);

      await transcribeAudio(uri);

    } catch (error) {
      console.error(
        "Stop recording error:",
        error
      );

      setRecording(false);
      setLoading(false);

      Alert.alert(
        "Recording Error",
        "Could not process the recording."
      );
    }
  };

  // ====================================================
  // VOICE BUTTON
  // ====================================================

  const handleVoiceButton = async () => {
    if (loading) {
      return;
    }

    if (recording) {
      await stopRecording();
    } else {
      await startRecording();
    }
  };

  // ====================================================
  // CLEAR
  // ====================================================

  const clearResults = () => {
    setQuestion("");
    setAnswer("");
    setScholarships([]);
    setAudioUri(null);
    setLoading(false);
  };

  // ====================================================
  // FORMAT CATEGORY
  // ====================================================

  const formatCategory = (
    category?: string | string[]
  ) => {
    if (!category) {
      return "";
    }

    if (Array.isArray(category)) {
      return category.join(", ");
    }

    return category;
  };

  // ====================================================
  // RENDER
  // ====================================================

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      {/* ==================================================
          HEADER
      ================================================== */}

      <View style={styles.header}>
        <Text style={styles.logo}>
          🎓
        </Text>

        <Text style={styles.title}>
          ScholarAI
        </Text>

        <Text style={styles.subtitle}>
          Your AI scholarship assistant
        </Text>
      </View>

      {/* ==================================================
          QUESTION CARD
      ================================================== */}

      <View style={styles.questionCard}>
        <Text style={styles.sectionTitle}>
          Ask about scholarships
        </Text>

        <Text style={styles.helperText}>
          Type your question or ask using your voice.
        </Text>

        {/* TEXT INPUT */}

        <TextInput
          style={styles.input}
          placeholder="Example: What scholarships are available for SC students?"
          placeholderTextColor="#8A8A8A"
          value={question}
          onChangeText={setQuestion}
          multiline
          textAlignVertical="top"
          editable={!loading && !recording}
        />

        {/* VOICE BUTTON */}

        <Pressable
          style={({ pressed }) => [
            styles.voiceButton,

            recording &&
              styles.recordingButton,

            loading &&
              styles.disabledButton,

            pressed &&
              styles.pressed,
          ]}
          onPress={handleVoiceButton}
          disabled={loading}
        >
          <Text style={styles.voiceIcon}>
            {recording ? "⏹" : "🎤"}
          </Text>

          <Text style={styles.voiceButtonText}>
            {recording
              ? "Stop Recording"
              : loading
              ? "Processing..."
              : "Ask by Voice"}
          </Text>
        </Pressable>

        {/* RECORDING STATUS */}

        {recording && (
          <View style={styles.recordingStatus}>
            <View
              style={styles.recordingDot}
            />

            <Text
              style={styles.recordingText}
            >
              Listening... Speak your question
            </Text>
          </View>
        )}

        {/* VOICE PROCESSING STATUS */}

        {loading &&
          audioUri &&
          !recording && (
            <View style={styles.processingStatus}>
              <ActivityIndicator
                size="small"
              />

              <Text
                style={styles.processingText}
              >
                Converting your voice to text...
              </Text>
            </View>
          )}

        {/* VOICE READY */}

        {audioUri &&
          !recording &&
          !loading && (
            <Text
              style={styles.audioReady}
            >
              ✅ Voice question processed
            </Text>
          )}

        {/* ASK BUTTON */}

        <Pressable
          style={({ pressed }) => [
            styles.askButton,

            pressed &&
              styles.pressed,

            loading &&
              styles.disabledButton,
          ]}
          onPress={() => askScholarship()}
          disabled={loading || recording}
        >
          {loading ? (
            <>
              <ActivityIndicator
                color="#FFFFFF"
              />

              <Text
                style={styles.buttonText}
              >
                Finding scholarships...
              </Text>
            </>
          ) : (
            <Text
              style={styles.buttonText}
            >
              ✨ Ask Scholarship Assistant
            </Text>
          )}
        </Pressable>

        {/* CLEAR */}

        {(question ||
          answer ||
          scholarships.length > 0) && (
          <Pressable
            style={styles.clearButton}
            onPress={clearResults}
            disabled={loading}
          >
            <Text
              style={styles.clearText}
            >
              Clear
            </Text>
          </Pressable>
        )}
      </View>

      {/* ==================================================
          AI ANSWER
      ================================================== */}

      {answer !== "" && (
        <View style={styles.answerCard}>
          <View
            style={styles.answerHeader}
          >
            <Text
              style={styles.answerIcon}
            >
              🤖
            </Text>

            <Text
              style={styles.sectionTitle}
            >
              AI Answer
            </Text>
          </View>

          <Text
            style={styles.answerText}
          >
            {answer}
          </Text>
        </View>
      )}

      {/* ==================================================
          MATCHING SCHOLARSHIPS
      ================================================== */}

      {scholarships.length > 0 && (
        <View
          style={styles.scholarshipSection}
        >
          <View
            style={styles.resultsHeader}
          >
            <Text
              style={styles.sectionTitle}
            >
              🎓 Matching Scholarships
            </Text>

            <Text
              style={styles.resultCount}
            >
              {scholarships.length} found
            </Text>
          </View>

          {scholarships.map(
            (scholarship, index) => (
              <View
                key={
                  scholarship.id ||
                  `scholarship-${index}`
                }
                style={
                  styles.scholarshipCard
                }
              >
                {/* NAME */}

                <Text
                  style={
                    styles.scholarshipName
                  }
                >
                  {scholarship.name ||
                    "Scholarship"}
                </Text>

                {/* CATEGORY */}

                {scholarship.category && (
                  <InfoRow
                    icon="👤"
                    label="Category"
                    value={formatCategory(
                      scholarship.category
                    )}
                  />
                )}

                {/* LEVEL */}

                {scholarship.level && (
                  <InfoRow
                    icon="🎓"
                    label="Level"
                    value={
                      scholarship.level
                    }
                  />
                )}

                {/* COURSE */}

                {scholarship.class_range && (
                  <InfoRow
                    icon="📚"
                    label="Course"
                    value={
                      scholarship.class_range
                    }
                  />
                )}

                {/* INCOME */}

                {scholarship.income_max !==
                  undefined &&
                  scholarship.income_max !==
                    null && (
                    <InfoRow
                      icon="💰"
                      label="Maximum family income"
                      value={`₹${Number(
                        scholarship.income_max
                      ).toLocaleString(
                        "en-IN"
                      )}`}
                    />
                  )}

                {/* MARKS */}

                {scholarship.marks_min !==
                  undefined &&
                  scholarship.marks_min !==
                    null && (
                    <InfoRow
                      icon="📊"
                      label="Minimum marks"
                      value={`${scholarship.marks_min}%`}
                    />
                  )}

                {/* BENEFIT */}

                {scholarship.benefit && (
                  <DetailBox
                    title="💰 Benefit"
                    text={
                      scholarship.benefit
                    }
                  />
                )}

                {/* DOCUMENTS */}

                {scholarship.documents &&
                  scholarship.documents.length >
                    0 && (
                    <View
                      style={
                        styles.detailBox
                      }
                    >
                      <Text
                        style={
                          styles.detailTitle
                        }
                      >
                        📄 Required Documents
                      </Text>

                      {scholarship.documents.map(
                        (
                          document,
                          documentIndex
                        ) => (
                          <Text
                            key={
                              documentIndex
                            }
                            style={
                              styles.detailText
                            }
                          >
                            • {document}
                          </Text>
                        )
                      )}
                    </View>
                  )}

                {/* HOW TO APPLY */}

                {scholarship.how_to_apply && (
                  <DetailBox
                    title="📝 How to Apply"
                    text={
                      scholarship.how_to_apply
                    }
                  />
                )}

                {/* DEADLINE */}

                {scholarship.deadline && (
                  <DetailBox
                    title="📅 Deadline"
                    text={
                      scholarship.deadline
                    }
                  />
                )}

                {/* SOURCE */}

                {scholarship.source && (
                  <Text
                    style={
                      styles.sourceText
                    }
                  >
                    Source:{" "}
                    {scholarship.source}
                  </Text>
                )}

                {/* NOTES */}

                {scholarship.notes && (
                  <DetailBox
                    title="ℹ️ Notes"
                    text={
                      scholarship.notes
                    }
                  />
                )}
              </View>
            )
          )}
        </View>
      )}

      {/* ==================================================
          EMPTY STATE
      ================================================== */}

      {!loading &&
        !answer &&
        scholarships.length === 0 && (
          <View
            style={styles.emptyCard}
          >
            <Text
              style={styles.emptyIcon}
            >
              🔎
            </Text>

            <Text
              style={styles.emptyTitle}
            >
              Find the right scholarship
            </Text>

            <Text
              style={styles.emptyText}
            >
              Ask about eligibility, income limits,
              benefits, documents, deadlines,
              or how to apply.
            </Text>
          </View>
        )}

      {/* FOOTER */}

      <Text style={styles.footer}>
        ScholarAI • Scholarship Information Assistant
      </Text>
    </ScrollView>
  );
}

// ======================================================
// INFO ROW COMPONENT
// ======================================================

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: string;
  label: string;
  value: string;
}) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoIcon}>
        {icon}
      </Text>

      <View style={styles.infoContent}>
        <Text
          style={styles.infoLabel}
        >
          {label}
        </Text>

        <Text
          style={styles.infoValue}
        >
          {value}
        </Text>
      </View>
    </View>
  );
}

// ======================================================
// DETAIL BOX COMPONENT
// ======================================================

function DetailBox({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <View style={styles.detailBox}>
      <Text
        style={styles.detailTitle}
      >
        {title}
      </Text>

      <Text
        style={styles.detailText}
      >
        {text}
      </Text>
    </View>
  );
}

// ======================================================
// STYLES
// ======================================================

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    paddingHorizontal: 20,
    paddingTop: 55,
    paddingBottom: 40,
    backgroundColor: "#F5F7FB",
  },

  header: {
    alignItems: "center",
    marginBottom: 28,
  },

  logo: {
    fontSize: 48,
    marginBottom: 5,
  },

  title: {
    fontSize: 32,
    fontWeight: "800",
    color: "#171717",
  },

  subtitle: {
    fontSize: 16,
    color: "#666666",
    marginTop: 6,
  },

  questionCard: {
    backgroundColor: "#FFFFFF",
    padding: 20,
    borderRadius: 20,
    marginBottom: 20,

    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 10,

    shadowOffset: {
      width: 0,
      height: 4,
    },

    elevation: 2,
  },

  sectionTitle: {
    fontSize: 21,
    fontWeight: "800",
    color: "#171717",
  },

  helperText: {
    fontSize: 14,
    color: "#777777",
    marginTop: 6,
    marginBottom: 15,
  },

  input: {
    minHeight: 105,
    borderWidth: 1,
    borderColor: "#D9DDE7",
    borderRadius: 14,
    padding: 15,
    fontSize: 16,
    color: "#222222",
    backgroundColor: "#FAFBFD",
    textAlignVertical: "top",
  },

  voiceButton: {
    marginTop: 12,
    minHeight: 52,
    borderRadius: 13,

    borderWidth: 1,
    borderColor: "#4F46E5",

    alignItems: "center",
    justifyContent: "center",

    flexDirection: "row",
    gap: 8,
  },

  recordingButton: {
    borderColor: "#DC2626",
    backgroundColor: "#FEF2F2",
  },

  voiceIcon: {
    fontSize: 19,
  },

  voiceButtonText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#4F46E5",
  },

  recordingStatus: {
    marginTop: 12,

    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },

  recordingDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
    backgroundColor: "#DC2626",
    marginRight: 8,
  },

  recordingText: {
    color: "#DC2626",
    fontSize: 13,
    fontWeight: "600",
  },

  processingStatus: {
    marginTop: 12,

    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },

  processingText: {
    color: "#4F46E5",
    fontSize: 13,
    fontWeight: "600",
  },

  audioReady: {
    textAlign: "center",
    color: "#047857",
    fontSize: 13,
    fontWeight: "600",
    marginTop: 10,
  },

  askButton: {
    marginTop: 15,
    minHeight: 56,

    paddingHorizontal: 16,

    borderRadius: 14,
    backgroundColor: "#4F46E5",

    alignItems: "center",
    justifyContent: "center",

    flexDirection: "row",
    gap: 8,
  },

  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },

  disabledButton: {
    opacity: 0.7,
  },

  pressed: {
    opacity: 0.75,
  },

  clearButton: {
    alignItems: "center",
    marginTop: 14,
  },

  clearText: {
    color: "#666666",
    fontSize: 14,
    fontWeight: "600",
  },

  answerCard: {
    backgroundColor: "#FFFFFF",
    padding: 20,
    borderRadius: 20,
    marginBottom: 20,

    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 10,

    shadowOffset: {
      width: 0,
      height: 4,
    },

    elevation: 2,
  },

  answerHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },

  answerIcon: {
    fontSize: 25,
    marginRight: 8,
  },

  answerText: {
    fontSize: 16,
    lineHeight: 25,
    color: "#333333",
  },

  scholarshipSection: {
    marginTop: 5,
  },

  resultsHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 14,
  },

  resultCount: {
    fontSize: 13,
    color: "#666666",
  },

  scholarshipCard: {
    backgroundColor: "#FFFFFF",
    padding: 20,
    borderRadius: 20,
    marginBottom: 18,

    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 8,

    shadowOffset: {
      width: 0,
      height: 3,
    },

    elevation: 2,
  },

  scholarshipName: {
    fontSize: 20,
    fontWeight: "800",
    color: "#171717",
    marginBottom: 15,
    lineHeight: 27,
  },

  infoRow: {
    flexDirection: "row",
    marginBottom: 12,
  },

  infoIcon: {
    fontSize: 17,
    width: 28,
  },

  infoContent: {
    flex: 1,
  },

  infoLabel: {
    fontSize: 12,
    color: "#888888",
    marginBottom: 2,
  },

  infoValue: {
    fontSize: 15,
    color: "#333333",
    lineHeight: 21,
  },

  detailBox: {
    marginTop: 14,
    paddingTop: 13,

    borderTopWidth: 1,
    borderTopColor: "#EEEEEE",
  },

  detailTitle: {
    fontSize: 15,
    fontWeight: "800",
    color: "#333333",
    marginBottom: 6,
  },

  detailText: {
    fontSize: 14,
    lineHeight: 22,
    color: "#4A4A4A",
  },

  sourceText: {
    marginTop: 15,
    fontSize: 12,
    lineHeight: 18,
    color: "#888888",
  },

  emptyCard: {
    backgroundColor: "#FFFFFF",
    padding: 25,
    borderRadius: 20,

    alignItems: "center",
    marginTop: 5,
  },

  emptyIcon: {
    fontSize: 40,
    marginBottom: 10,
  },

  emptyTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#333333",
    textAlign: "center",
  },

  emptyText: {
    marginTop: 8,
    fontSize: 14,
    lineHeight: 21,
    color: "#777777",
    textAlign: "center",
  },

  footer: {
    textAlign: "center",
    fontSize: 12,
    color: "#999999",
    marginTop: 25,
  },
});
