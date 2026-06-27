## 2026-06-27 - Server Status Badge Accessibility
**Learning:** Screen readers struggle to correctly interpret icon-only or dynamic visual status indicators (like pulsing dots) when their structural meaning isn't clearly defined. Wrapping them in a simple `div` without semantics causes context to be lost.
**Action:** Always add `role="status"` and a descriptive `aria-label` to dynamic status containers, and explicitly hide decorative pulsing dot elements with `aria-hidden="true"`.
