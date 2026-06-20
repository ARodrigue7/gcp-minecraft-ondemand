## 2024-06-25 - Improved Form Accessibility and Live Status Announcements
**Learning:** Found inputs relying solely on placeholders and server status indicators lacking ARIA live regions. Screen readers miss updates when status checks poll the server if they don't have `role="status"` and `aria-live="polite"`. Additionally, relying solely on placeholder text for forms fails screen reader accessibility since the placeholder text often disappears.
**Action:** Always include semantic labels linked by `id`, ensure active UI status elements have `aria-live` or `role="status"`, and implement focus-visible styles across interactive elements.
## 2026-06-20 - ARIA Enhancements on Status Notifications
**Learning:** Found status elements missing ARIA attributes, causing screen readers to miss dynamic updates.
**Action:** Consistently apply `role="alert"`/`role="status"` and `aria-live` to dynamic status wrappers to ensure accessibility.
