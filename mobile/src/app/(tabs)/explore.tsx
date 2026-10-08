import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import {
  AudioModule,
  RecordingPresets,
  useAudioRecorder,
} from 'expo-audio';

import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';
import {
  BottomTabInset,
  MaxContentWidth,
  Spacing,
} from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';


export default function TabTwoScreen() {

  // --------------------------------------------------
  // Theme and safe area
  // --------------------------------------------------

  const theme = useTheme();
  const safeAreaInsets = useSafeAreaInsets();

  const insets = {
    ...safeAreaInsets,
    bottom:
      safeAreaInsets.bottom +
      BottomTabInset +
      Spacing.three,
  };


  // --------------------------------------------------
  // Voice recording state
  // --------------------------------------------------

  const [recording, setRecording] = useState(false);
  const [audioUri, setAudioUri] = useState<string | null>(null);
  const [permissionDenied, setPermissionDenied] =
    useState(false);


  // --------------------------------------------------
  // Audio recorder
  // --------------------------------------------------

  const audioRecorder = useAudioRecorder(
    RecordingPresets.HIGH_QUALITY
  );


  // --------------------------------------------------
  // Request microphone permission
  // --------------------------------------------------

  useEffect(() => {

    const requestPermission = async () => {

      try {

        const result =
          await AudioModule.requestRecordingPermissionsAsync();

        if (!result.granted) {
          setPermissionDenied(true);
        }

      } catch (error) {

        console.error(
          'Microphone permission error:',
          error
        );

        setPermissionDenied(true);
      }
    };

    requestPermission();

  }, []);


  // --------------------------------------------------
  // Start recording
  // --------------------------------------------------

  const startRecording = async () => {

    try {

      setAudioUri(null);

      await audioRecorder.prepareToRecordAsync();

      audioRecorder.record();

      setRecording(true);

      console.log('🎤 Recording started');

    } catch (error) {

      console.error(
        'Start recording error:',
        error
      );

    }
  };


  // --------------------------------------------------
  // Stop recording
  // --------------------------------------------------

  const stopRecording = async () => {

    try {

      await audioRecorder.stop();

      setRecording(false);

      const uri = audioRecorder.uri;

      if (uri) {
        setAudioUri(uri);

        console.log(
          '✅ Recording completed:',
          uri
        );
      }

    } catch (error) {

      console.error(
        'Stop recording error:',
        error
      );

      setRecording(false);
    }
  };


  // --------------------------------------------------
  // Button handler
  // --------------------------------------------------

  const handleVoiceButton = async () => {

    if (recording) {
      await stopRecording();
    } else {
      await startRecording();
    }
  };


  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (

    <ScrollView
      style={[
        styles.scrollView,
        {
          backgroundColor: theme.background,
        },
      ]}
      contentContainerStyle={[
        styles.contentContainer,
        {
          paddingTop: insets.top + Spacing.four,
          paddingBottom: insets.bottom,
        },
      ]}
    >

      <ThemedView style={styles.container}>

        {/* -------------------------------------------- */}
        {/* Header */}
        {/* -------------------------------------------- */}

        <View style={styles.header}>

          <Text style={styles.logo}>
            🎓
          </Text>

          <ThemedText
            type="title"
            style={styles.title}
          >
            ScholarAI
          </ThemedText>

          <ThemedText
            style={styles.subtitle}
            themeColor="textSecondary"
          >
            Your scholarship assistant
          </ThemedText>

        </View>


        {/* -------------------------------------------- */}
        {/* Voice Card */}
        {/* -------------------------------------------- */}

        <View
          style={[
            styles.voiceCard,
            {
              backgroundColor:
                theme.backgroundElement,
            },
          ]}
        >

          <Text style={styles.microphone}>
            {recording ? '🔴' : '🎤'}
          </Text>

          <ThemedText
            type="subtitle"
            style={styles.voiceTitle}
          >
            {recording
              ? 'Listening...'
              : 'Ask by Voice'}
          </ThemedText>


          <ThemedText
            style={styles.voiceDescription}
            themeColor="textSecondary"
          >
            {recording
              ? 'Speak your scholarship question'
              : 'Tap the button and ask your scholarship question'}
          </ThemedText>


          {/* ------------------------------------------ */}
          {/* Record Button */}
          {/* ------------------------------------------ */}

          <Pressable
            onPress={handleVoiceButton}
            disabled={permissionDenied}
            style={({ pressed }) => [
              styles.recordButton,

              recording
                ? styles.stopButton
                : styles.startButton,

              pressed && styles.pressed,

              permissionDenied &&
                styles.disabledButton,
            ]}
          >

            {recording ? (

              <>

                <Text style={styles.buttonIcon}>
                  ⏹
                </Text>

                <Text style={styles.buttonText}>
                  Stop Recording
                </Text>

              </>

            ) : (

              <>

                <Text style={styles.buttonIcon}>
                  🎤
                </Text>

                <Text style={styles.buttonText}>
                  Start Recording
                </Text>

              </>

            )}

          </Pressable>


          {/* ------------------------------------------ */}
          {/* Permission message */}
          {/* ------------------------------------------ */}

          {permissionDenied && (

            <Text style={styles.errorText}>
              Microphone permission is required
              to use voice input.
            </Text>

          )}


          {/* ------------------------------------------ */}
          {/* Recording completed */}
          {/* ------------------------------------------ */}

          {audioUri && !recording && (

            <View style={styles.completedBox}>

              <Text style={styles.completedIcon}>
                ✅
              </Text>

              <View style={styles.completedContent}>

                <Text style={styles.completedTitle}>
                  Recording completed
                </Text>

                <Text style={styles.completedText}>
                  Your voice recording is ready.
                </Text>

              </View>

            </View>

          )}

        </View>


        {/* -------------------------------------------- */}
        {/* How it works */}
        {/* -------------------------------------------- */}

        <View style={styles.howItWorks}>

          <ThemedText
            type="subtitle"
            style={styles.sectionTitle}
          >
            How it works
          </ThemedText>


          <View style={styles.step}>

            <View style={styles.stepCircle}>
              <Text style={styles.stepNumber}>
                1
              </Text>
            </View>

            <View style={styles.stepContent}>

              <Text style={styles.stepTitle}>
                🎤 Speak
              </Text>

              <Text style={styles.stepText}>
                Ask your scholarship question using
                your voice.
              </Text>

            </View>

          </View>


          <View style={styles.step}>

            <View style={styles.stepCircle}>
              <Text style={styles.stepNumber}>
                2
              </Text>
            </View>

            <View style={styles.stepContent}>

              <Text style={styles.stepTitle}>
                📝 Speech to Text
              </Text>

              <Text style={styles.stepText}>
                Whisper converts your voice into text.
              </Text>

            </View>

          </View>


          <View style={styles.step}>

            <View style={styles.stepCircle}>
              <Text style={styles.stepNumber}>
                3
              </Text>
            </View>

            <View style={styles.stepContent}>

              <Text style={styles.stepTitle}>
                🤖 AI Scholarship Search
              </Text>

              <Text style={styles.stepText}>
                Our RAG system searches the scholarship
                database and generates an answer.
              </Text>

            </View>

          </View>


          <View style={styles.step}>

            <View style={styles.stepCircle}>
              <Text style={styles.stepNumber}>
                4
              </Text>
            </View>

            <View style={styles.stepContent}>

              <Text style={styles.stepTitle}>
                🔊 Listen
              </Text>

              <Text style={styles.stepText}>
                The final answer can be converted
                into speech using gTTS.
              </Text>

            </View>

          </View>

        </View>


        {/* -------------------------------------------- */}
        {/* Current status */}
        {/* -------------------------------------------- */}

        <View style={styles.statusCard}>

          <Text style={styles.statusIcon}>
            {recording ? '🟢' : '⚪'}
          </Text>

          <View style={styles.statusContent}>

            <Text style={styles.statusTitle}>
              Voice Assistant
            </Text>

            <Text style={styles.statusText}>
              {recording
                ? 'Recording your question...'
                : audioUri
                  ? 'Recording saved successfully'
                  : 'Ready to record'}
            </Text>

          </View>

        </View>


        {/* Web information */}
        {Platform.OS === 'web' && (

          <Text style={styles.webNote}>
            For the best microphone experience,
            test this feature on an Android or iOS
            device using Expo Go.
          </Text>

        )}

      </ThemedView>

    </ScrollView>

  );
}


// ==================================================
// Styles
// ==================================================

const styles = StyleSheet.create({

  scrollView: {
    flex: 1,
  },

  contentContainer: {
    flexGrow: 1,
    alignItems: 'center',
    paddingHorizontal: Spacing.four,
  },

  container: {
    width: '100%',
    maxWidth: MaxContentWidth,
    flexGrow: 1,
  },


  // -----------------------------------------------
  // Header
  // -----------------------------------------------

  header: {
    alignItems: 'center',
    paddingVertical: Spacing.four,
  },

  logo: {
    fontSize: 48,
    marginBottom: 6,
  },

  title: {
    fontSize: 30,
    fontWeight: '700',
  },

  subtitle: {
    marginTop: 6,
    fontSize: 16,
  },


  // -----------------------------------------------
  // Voice card
  // -----------------------------------------------

  voiceCard: {
    borderRadius: 24,
    padding: 28,
    alignItems: 'center',
    marginTop: Spacing.three,
  },

  microphone: {
    fontSize: 64,
    marginBottom: 15,
  },

  voiceTitle: {
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center',
  },

  voiceDescription: {
    textAlign: 'center',
    fontSize: 15,
    lineHeight: 22,
    marginTop: 10,
    marginBottom: 25,
  },


  // -----------------------------------------------
  // Buttons
  // -----------------------------------------------

  recordButton: {
    width: '100%',
    minHeight: 58,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 10,
  },

  startButton: {
    backgroundColor: '#4F46E5',
  },

  stopButton: {
    backgroundColor: '#DC2626',
  },

  disabledButton: {
    opacity: 0.5,
  },

  pressed: {
    opacity: 0.75,
  },

  buttonIcon: {
    fontSize: 20,
  },

  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },


  // -----------------------------------------------
  // Permission / error
  // -----------------------------------------------

  errorText: {
    color: '#DC2626',
    textAlign: 'center',
    marginTop: 15,
    lineHeight: 20,
  },


  // -----------------------------------------------
  // Completed recording
  // -----------------------------------------------

  completedBox: {
    width: '100%',
    marginTop: 20,
    padding: 15,
    borderRadius: 14,
    backgroundColor: '#ECFDF5',
    flexDirection: 'row',
    alignItems: 'center',
  },

  completedIcon: {
    fontSize: 25,
    marginRight: 12,
  },

  completedContent: {
    flex: 1,
  },

  completedTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#065F46',
  },

  completedText: {
    fontSize: 13,
    marginTop: 3,
    color: '#047857',
  },


  // -----------------------------------------------
  // How it works
  // -----------------------------------------------

  howItWorks: {
    marginTop: 28,
  },

  sectionTitle: {
    fontSize: 21,
    fontWeight: '700',
    marginBottom: 18,
  },

  step: {
    flexDirection: 'row',
    marginBottom: 20,
  },

  stepCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#4F46E5',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },

  stepNumber: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },

  stepContent: {
    flex: 1,
  },

  stepTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 4,
  },

  stepText: {
    fontSize: 14,
    lineHeight: 21,
    color: '#666666',
  },


  // -----------------------------------------------
  // Status
  // -----------------------------------------------

  statusCard: {
    marginTop: 10,
    padding: 16,
    borderRadius: 16,
    backgroundColor: '#F3F4F6',
    flexDirection: 'row',
    alignItems: 'center',
  },

  statusIcon: {
    fontSize: 22,
    marginRight: 12,
  },

  statusContent: {
    flex: 1,
  },

  statusTitle: {
    fontSize: 15,
    fontWeight: '700',
  },

  statusText: {
    fontSize: 13,
    color: '#666666',
    marginTop: 3,
  },


  // -----------------------------------------------
  // Web note
  // -----------------------------------------------

  webNote: {
    textAlign: 'center',
    fontSize: 12,
    color: '#777777',
    marginTop: 20,
    marginBottom: 20,
    lineHeight: 18,
  },

});
