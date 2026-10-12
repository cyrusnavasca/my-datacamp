import { describe, expect, it } from "vitest";
import { getCourse } from "@/lib/content/loader";
import { trackCourses } from "@/lib/course-progress";

// BUG-001: one broken file must not take down every page that lists courses.
describe("broken content is contained", () => {
  it("a broken lesson file marks only that lesson", () => {
    const c = getCourse("demo")!;
    const bad = c.chapters[2].lessons[0];
    expect(bad.exercises).toBeNull();
    expect(bad.error).toMatch(/bad\.yaml/);
    expect(c.exerciseCount).toBe(6);
  });

  it("a broken course.yaml shows up as an error in its track, not a crash", () => {
    const items = trackCourses(["demo", "broken"]);
    expect(items[0].course?.title).toBe("Demo");
    expect(items[1].course).toBeNull();
    expect(items[1].error).toMatch(/broken\/course\.yaml/);
  });
});
