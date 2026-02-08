"use client";

import { useEffect } from "react";

const CLICKABLE_SELECTOR = [
  "a[href]",
  "button:not(:disabled)",
  "[role=\"button\"]:not([aria-disabled=\"true\"])",
  "input[type=\"button\"]:not(:disabled)",
  "input[type=\"submit\"]:not(:disabled)",
  "input[type=\"reset\"]:not(:disabled)",
  "summary",
  "label[for]",
  "[onclick]",
  "[tabindex]:not([tabindex=\"-1\"])",
].join(",");

export default function CursorGuard() {
  useEffect(() => {
    let rafId = 0;
    let mouseX = -1;
    let mouseY = -1;
    let pointerExpiry = 0;
    let forcePointer = false;

    const setForcePointer = (enabled: boolean) => {
      if (forcePointer === enabled) return;
      forcePointer = enabled;

      if (enabled) {
        document.documentElement.setAttribute("data-force-pointer", "true");
      } else {
        document.documentElement.removeAttribute("data-force-pointer");
      }
    };

    const isClickableAtPoint = (x: number, y: number) => {
      const stack = document.elementsFromPoint(x, y);
      for (const node of stack) {
        if (!(node instanceof Element)) continue;
        if (node.matches(CLICKABLE_SELECTOR) || node.closest(CLICKABLE_SELECTOR)) {
          return true;
        }
      }
      return false;
    };

    const evaluate = () => {
      const now = performance.now();
      const hasMouse = mouseX >= 0 && mouseY >= 0;
      const clickableNow = hasMouse ? isClickableAtPoint(mouseX, mouseY) : false;

      if (clickableNow) {
        pointerExpiry = now + 140;
        setForcePointer(true);
      } else if (now > pointerExpiry) {
        setForcePointer(false);
      }

      rafId = window.requestAnimationFrame(evaluate);
    };

    const onMove = (event: MouseEvent) => {
      mouseX = event.clientX;
      mouseY = event.clientY;
    };

    const onLeaveWindow = () => {
      mouseX = -1;
      mouseY = -1;
      pointerExpiry = 0;
      setForcePointer(false);
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseleave", onLeaveWindow);
    rafId = window.requestAnimationFrame(evaluate);

    return () => {
      window.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseleave", onLeaveWindow);
      window.cancelAnimationFrame(rafId);
      document.documentElement.removeAttribute("data-force-pointer");
    };
  }, []);

  return null;
}
