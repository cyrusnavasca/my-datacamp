import { PageHeader } from "@/components/ui";
import { listTracks } from "@/lib/content/loader";
import { safeGetCourse } from "@/lib/course-progress";
import { dailyGoal, getSetting } from "@/lib/progress";
import { SettingsForm } from "./SettingsForm";

export default function SettingsPage() {
  const courses = listTracks()
    .flatMap((t) => t.courses)
    .map((slug) => ({ slug, title: safeGetCourse(slug).course?.title ?? slug }));
  return (
    <>
      <PageHeader title="Settings" />
      <SettingsForm goal={dailyGoal()} theme={getSetting("theme", "system")} courses={courses} />
    </>
  );
}
