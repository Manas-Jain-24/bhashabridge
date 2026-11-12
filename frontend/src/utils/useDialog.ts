import {useEffect, useRef} from 'react';
const stack: HTMLElement[] = [];

export function useDialog(open: boolean) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current;
    if (!open || !element) return;
    const previous = document.activeElement as HTMLElement | null;
    stack.push(element);
    const focusable = () => Array.from(element.querySelectorAll<HTMLElement>(
      'button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]'
    )).filter(item => item.getClientRects().length > 0);
    (focusable()[0] || element).focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key !== 'Tab' || stack[stack.length-1] !== element) return;
      const items = focusable();
      const first = items[0] || element, last = items[items.length-1] || element;
      if (event.shiftKey && (document.activeElement === first || document.activeElement === element)) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !element.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    };
    document.addEventListener('keydown', keydown);
    return () => {
      document.removeEventListener('keydown', keydown);
      const index = stack.indexOf(element); if (index >= 0) stack.splice(index, 1);
      if (previous?.isConnected) previous.focus();
    };
  }, [open]);
  return ref;
}
