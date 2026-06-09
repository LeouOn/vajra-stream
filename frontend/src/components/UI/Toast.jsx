/**
 * Toast — auto-dismissing notification toasts.
 *
 * Backed by Antd's `notification` API. The store's addToast()
 * still pushes a toast into state.toasts; this component subscribes
 * to that array, mirrors new toasts into Antd's notification stack,
 * and removes the mirror when the store removes the toast.
 *
 * Why: the previous implementation hand-rolled icons, colors,
 * positioning, and ARIA semantics that Antd provides out of the
 * box. The hand-rolled version was 110+ lines; the Antd version is
 * a thin subscription.
 *
 * Position: topRight (matches the previous fixed top-4 right-4 layout).
 *
 * Supported types: 'success' | 'error' | 'warning' | 'info'.
 * The store defaults to 'info' if no type is provided.
 *
 * @component
 */
import { useEffect, useRef } from 'react';
import { notification } from 'antd';
import { useUIStore } from '../../stores/uiStore';

// Antd's notification key is a string; our store uses numbers.
// Keep a side-table so removeToast(id) can find the matching Antd key.
const idToAntdKey = new Map();
let antdKeyCounter = 0;

const TYPE_TO_API = {
  success: notification.success,
  error: notification.error,
  warning: notification.warning,
  info: notification.info,
};

const ToastBridge = () => {
  const toasts = useUIStore((s) => s.toasts);
  // Track which toast ids we've already mirrored into Antd, so we
  // only call notification.* once per toast (Antd is a push API,
  // not a render API).
  const mirroredRef = useRef(new Set());

  useEffect(() => {
    const mirrored = mirroredRef.current;
    const currentIds = new Set(toasts.map((t) => t.id));

    // Mirror new toasts into Antd
    toasts.forEach((toast) => {
      if (mirrored.has(toast.id)) return;
      mirrored.add(toast.id);

      const api = TYPE_TO_API[toast.type] || notification.info;
      const antdKey = `toast-${++antdKeyCounter}`;
      idToAntdKey.set(toast.id, antdKey);

      api({
        key: antdKey,
        message: toast.title || undefined,
        description: toast.message || undefined,
        placement: 'topRight',
        duration: toast.duration ?? 4.5,
        btn: toast.action ? (
          <button
            type="button"
            onClick={() => {
              toast.action.onClick();
              useUIStore.getState().removeToast(toast.id);
            }}
            style={{ color: 'inherit', background: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 600 }}
          >
            {toast.action.label}
          </button>
        ) : undefined,
        onClose: () => {
          // Antd-driven close (timeout or user X click) — clean up our side-table
          idToAntdKey.delete(toast.id);
          mirrored.delete(toast.id);
        },
      });
    });

    // Mirror removals: any id we previously mirrored that is no
    // longer in the store was removed via removeToast().
    mirrored.forEach((id) => {
      if (!currentIds.has(id)) {
        const antdKey = idToAntdKey.get(id);
        if (antdKey) {
          notification.destroy(antdKey);
          idToAntdKey.delete(id);
        }
        mirrored.delete(id);
      }
    });
  }, [toasts]);

  return null;
};

export { ToastBridge as ToastContainer };
