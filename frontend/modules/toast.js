/**
 * RevenueOS Studio – Toast Notification System
 * ============================================
 * Provides user feedback with severity levels (info, success, warning, error).
 */

export function showToast(message, type = "info", duration = 3000) {
  const toast = document.createElement("div");
  toast.className = `pbi-toast toast-${type}`;
  toast.style.position = "fixed";
  toast.style.bottom = "42px";
  toast.style.right = "20px";
  toast.style.padding = "10px 18px";
  toast.style.borderRadius = "4px";
  toast.style.fontSize = "12px";
  toast.style.fontWeight = "600";
  toast.style.boxShadow = "0 4px 16px rgba(0,0,0,0.6)";
  toast.style.zIndex = "99999";
  toast.style.display = "flex";
  toast.style.alignItems = "center";
  toast.style.gap = "8px";
  toast.style.transition = "opacity 0.2s ease, transform 0.2s ease";

  let icon = "ℹ️";
  if (type === "success") {
    toast.style.backgroundColor = "var(--pbi-accent-green, #107C41)";
    toast.style.color = "#FFFFFF";
    icon = "✓";
  } else if (type === "error") {
    toast.style.backgroundColor = "var(--pbi-accent-red, #D83B01)";
    toast.style.color = "#FFFFFF";
    icon = "✕";
  } else if (type === "warning") {
    toast.style.backgroundColor = "var(--pbi-accent-gold, #FFB900)";
    toast.style.color = "#18181B";
    icon = "⚠";
  } else {
    toast.style.backgroundColor = "var(--pbi-accent-blue, #0078D4)";
    toast.style.color = "#FFFFFF";
  }

  toast.innerHTML = `<span style="font-weight:bold;">${icon}</span> <span>${message}</span>`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(8px)";
    setTimeout(() => toast.remove(), 200);
  }, duration);
}
