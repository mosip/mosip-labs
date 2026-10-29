---
topic: framework/uitestrig
scope: framework
status: Inferred (surface survey only; not profiled)
last_verified: 2026-10-27 (directory listing; not a git checkout)
---

# uitestrig-platform (post-MVP, phase P7)

Location: `UI_Automation/uitestrig-platform`. Maven multi-module: `uitest-commons`, `uitest-ai`, `uitest-browserstack` (`uitestrig-platform` 1.0.0-SNAPSHOT).
Stack: Playwright + Cucumber (`listeners/CucumberHooks`, `browser/PlaywrightFactory`).

Capabilities seen in `uitest-commons` (see `uitest-commons/SUMMARY.txt` for the team's own history):
pages/BasePage · elements/* (Button, TextBox, DropDown, DatePicker, Table, Dialog, Toast) · browser/SmartWait (Angular/network idle),
SelfHealingLocator, BrowserManager · assertions/AssertionLibrary, SoftAssertions, VisualValidator · visual/SnapshotManager,
VisualDiffEngine · accessibility/AccessibilityValidator (axe, WCAG levels) · reporting/KnownIssueManager, UiExtentReportManager.

Unknown, to be profiled before the UI agent is enabled: where feature files/step definitions live in consuming modules
(e.g. uitest-resident), the run command, report location, whether a coverage matrix exists for UI, and what `uitest-ai` does.
Note: the directory is not a git working tree, so branch/commit/DCO rules cannot apply until that is resolved.
