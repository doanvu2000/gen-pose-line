# Design system (port từ Gen Asset Studio)

Bộ style macOS-native của Gen Asset Studio, đóng gói cho frontend HTML/JS thuần của tool này.
Spec đầy đủ (tokens, typography, component, motion, layout, checklist): **[SPEC.md](SPEC.md)**.

## File

| File | Nội dung |
|---|---|
| `ds.css` | Entry: import toàn bộ theo đúng thứ tự |
| `fonts/` | Be Vietnam Pro 400–700 + JetBrains Mono 500 (woff2, subset vi/latin) |
| `tokens.css` | Màu light/dark, shadow, radius, easing, kích thước shell (`--on-accent` mới thêm) |
| `base.css` | Reset, body 14px, focus ring, scrollbar, reduced-motion |
| `components.css` | Nguyên bản: shell (titlebar/sidebar/statusbar), `.btn`, `.icon-btn`, `.seg`, `.chip`, `.bar`, `.sheet`/modal, settings group/row, setup card, empty-drop |
| `components-extra.css` | Gom từ các màn khác: form (`.fld .inp .ta .search .stepper .switch`), `.fchip`, `.card`, `.tile`, `.opt`, `.dlg`, `.drawer`, `.menu`, `.toast`, `.note`, `.tip`, `.log`, `.empty`, `.drop-ov`, `.spin`, `.skel`, keyframes |
| `motion.css` | Class thay cho preset `motion/react`: `.m-view-enter`, `.m-sheet-in/out`, `.m-toast-in/out`, `.m-drawer-in/out`, `.m-menu-in`, `.m-stagger` |
| `icons.js` | 48 icon SVG (stroke 1.8) — `icon(name, size)` hoặc `<i data-icon="check">` + `hydrateIcons()` |

## Dùng trong `static/index.html`

```html
<link rel="stylesheet" href="/static/design-system/ds.css">
<script type="module">
  import { icon, hydrateIcons } from '/static/design-system/icons.js'

  const mq = matchMedia('(prefers-color-scheme: dark)')
  const applyTheme = (pref = localStorage.getItem('theme') || 'system') => {
    document.documentElement.dataset.theme = pref === 'system' ? (mq.matches ? 'dark' : 'light') : pref
  }
  applyTheme()
  mq.addEventListener('change', () => applyTheme())
  hydrateIcons()
</script>
```


## Lưu ý khi chạy trên trình duyệt (không phải Electron)

- `base.css` đặt `body { overflow: hidden; user-select: none; }` cho layout app full-window.
  Nếu trang cần cuộn cả trang thì override `body { overflow: auto; }`.
- Bỏ `.lights` (traffic lights) và `-webkit-app-region` trong titlebar — chỉ dùng cho cửa sổ
  frameless. Titlebar vẫn giữ làm header (52px, chrome blur).
- Dialog: `.modal-root > .scrim + .sheet.dlg.m-sheet-in`; Esc + click scrim để đóng; khi đóng
  đổi sang `.m-sheet-out` rồi remove sau `animationend`.
- Toast: `.toasts > button.toast.ok|info|warn|err.m-toast-in` gồm icon 15px + `<span>`; tự tắt
  3.2s (ok/info) / 6s (warn/err), tối đa 4 cái.
- Segmented: `.seg > button(.on) > span.seg-thumb + span.seg-label` (thumb ở nút đang chọn;
  bản React trượt bằng layoutId, bản thuần chỉ cần chuyển thumb).
- Switch: `<button class="switch on" role="switch" aria-checked="true"><i></i></button>`.
