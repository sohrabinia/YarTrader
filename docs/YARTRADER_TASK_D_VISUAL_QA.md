==================================================
YARTRADER TASK D — VISUAL QA MATRIX
==================================================

Page / Screen | 375px | 390px | 768px | 1024px | 1440px | 1920px
Dashboard | PASS | PASS | PASS | PASS | PASS | PASS
Chat Widget | PASS | PASS | PASS | PASS | PASS | PASS
Backtest UI | PASS | PASS | PASS | PASS | PASS | PASS
Demo UI | PASS | PASS | PASS | PASS | PASS | PASS
Shadow UI | PASS | PASS | PASS | PASS | PASS | PASS
Live UI (Hard Blocked) | PASS | PASS | PASS | PASS | PASS | PASS
Signal Hub | PASS | PASS | PASS | PASS | PASS | PASS
Learning Matrix | PASS | PASS | PASS | PASS | PASS | PASS
Pricing UI | PASS | PASS | PASS | PASS | PASS | PASS
Admin Console | PASS | PASS | PASS | PASS | PASS | PASS

Layout Observations:
- Mobile Chat Drawer (375px/390px/768px): Pinned to viewport bottom with flexbox overflow handling, messages container scrollable, input field and retry buttons fully accessible.
- Tables (Backtest, Demo, Shadow, Learning, Admin): Enclosed in horizontal scroll wrappers (`overflowX: 'auto'`) preventing mobile viewport overflow.
- Top Header & Navigation: Flex-wrap applied with drawer sidebar on desktop and horizontal pill bar on tablet/mobile.

==================================================
END OF VISUAL QA MATRIX
==================================================
