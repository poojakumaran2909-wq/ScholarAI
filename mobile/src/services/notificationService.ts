import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

const CHANNEL_ID = "scholarship-deadlines";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function requestNotificationPermissions(): Promise<boolean> {
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync(
      CHANNEL_ID,
      {
        name: "Scholarship Deadlines",
        importance:
          Notifications.AndroidImportance.HIGH,
        sound: "default",
      }
    );
  }

  const {
    status: existingStatus,
  } =
    await Notifications.getPermissionsAsync();

  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } =
      await Notifications.requestPermissionsAsync();

    finalStatus = status;
  }

  return finalStatus === "granted";
}

function parseDeadline(
  deadline: string | null
): Date | null {
  if (!deadline) {
    return null;
  }

  // DD-MM-YYYY
  const dashDate = deadline.match(
    /^(\d{2})-(\d{2})-(\d{4})$/
  );

  if (dashDate) {
    return new Date(
      Number(dashDate[3]),
      Number(dashDate[2]) - 1,
      Number(dashDate[1]),
      23,
      59,
      59
    );
  }

  // DD/MM/YYYY
  const slashDate = deadline.match(
    /^(\d{2})\/(\d{2})\/(\d{4})$/
  );

  if (slashDate) {
    return new Date(
      Number(slashDate[3]),
      Number(slashDate[2]) - 1,
      Number(slashDate[1]),
      23,
      59,
      59
    );
  }

  // YYYY-MM-DD
  const isoDate = deadline.match(
    /^(\d{4})-(\d{2})-(\d{2})$/
  );

  if (isoDate) {
    return new Date(
      Number(isoDate[1]),
      Number(isoDate[2]) - 1,
      Number(isoDate[3]),
      23,
      59,
      59
    );
  }

  return null;
}

export async function cancelScholarshipNotifications(
  scholarshipId: string
): Promise<void> {
  const scheduled =
    await Notifications.getAllScheduledNotificationsAsync();

  const matching = scheduled.filter(
    notification => {
      const data =
        notification.content.data as
          | {
              scholarshipId?: string;
            }
          | undefined;

      return (
        data?.scholarshipId ===
        scholarshipId
      );
    }
  );

  await Promise.all(
    matching.map(notification =>
      Notifications.cancelScheduledNotificationAsync(
        notification.identifier
      )
    )
  );
}

export async function scheduleScholarshipDeadlineNotifications(
  scholarshipId: string,
  scholarshipName: string,
  deadline: string | null
): Promise<number> {
  const deadlineDate =
    parseDeadline(deadline);

  if (!deadlineDate) {
    return 0;
  }

  const permissionGranted =
    await requestNotificationPermissions();

  if (!permissionGranted) {
    return 0;
  }

  // Prevent duplicate notifications
  await cancelScholarshipNotifications(
    scholarshipId
  );

  const reminderDays = [7, 3, 1];

  let scheduledCount = 0;

  for (const daysBefore of reminderDays) {
    const reminderDate =
      new Date(deadlineDate);

    reminderDate.setDate(
      reminderDate.getDate() -
        daysBefore
    );

    // 9:00 AM
    reminderDate.setHours(
      9,
      0,
      0,
      0
    );

    // Don't schedule past reminders
    if (reminderDate <= new Date()) {
      continue;
    }

    await Notifications.scheduleNotificationAsync(
      {
        content: {
          title:
            "ScholarAI Deadline Reminder",

          body:
            daysBefore === 1
              ? `${scholarshipName} deadline is tomorrow.`
              : `${scholarshipName} deadline is in ${daysBefore} days.`,

          sound: "default",

          data: {
            scholarshipId,
            scholarshipName,
            deadline,
            daysBefore,
          },
        },

        trigger: {
          type:
            Notifications
              .SchedulableTriggerInputTypes
              .DATE,

          date: reminderDate,

          ...(Platform.OS === "android"
            ? {
                channelId:
                  CHANNEL_ID,
              }
            : {}),
        },
      }
    );

    scheduledCount++;
  }

  return scheduledCount;
}