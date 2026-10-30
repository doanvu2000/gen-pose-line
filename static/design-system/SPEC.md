# Gen Asset Studio — Design System Spec

Spec để dựng app mới cùng style. Nguồn: `src/renderer/src/styles/*.css`, `lib/motion.ts`,
`components/*.tsx` (version 1.1.1). Stack gốc: Electron + React 19 + `motion` (Framer Motion) +
zustand + i18next; CSS thuần với custom properties, không Tailwind.

---

## 1. Ngôn ngữ thiết kế

**"macOS-native desktop app"** — giống Finder / System Settings / Xcode:

- Nền xám nhạt `#F5F5F7`, surface trắng, accent xanh Apple `#0071E3`; dark mode theo palette
  macOS (`#1C1C1E` / `#2C2C2E`, accent `#0A84FF`).
- Chrome (titlebar, statusbar) mờ kính: nền bán trong suốt + `backdrop-filter: blur(24px)`.
- Viền mảnh `0.5px` gộp vào shadow (`0 0 0 .5px`), separator rgba thay vì màu đặc.
- Traffic lights tự vẽ (frameless window), icon nét 1.8px kiểu SF Symbols.
- Mật độ cao, chữ nhỏ (body 14px, phụ 11–12.5px), `tabular-nums` cho mọi số.
- Chuyển động: spring ngắn, nảy nhẹ; mọi thứ tôn trọng `prefers-reduced-motion`.
- Semantic color luôn đi cặp **text đậm + nền rgba nhạt** (`--green` + `--green-bg`), không
  dùng nền đặc trừ dot/progress.
- App desktop: `user-select: none` toàn cục, chỉ bật lại ở input/log/path; `cursor: default`
  cho button (không phải pointer).

---

## 2. Design tokens

Copy nguyên khối này thành `tokens.css`. Theme chuyển bằng `document.documentElement.dataset.theme
= 'light' | 'dark'` (resolve từ setting `system/light/dark` + `prefers-color-scheme`).

```css
:root {
  --font: "Be Vietnam Pro", -apple-system, "Segoe UI", system-ui, sans-serif;
  --display: "Be Vietnam Pro", -apple-system, "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", "Cascadia Code", Consolas, monospace;

  --accent: #0071E3;
  --accent-soft: rgba(0, 113, 227, .12);
  --accent-ring: rgba(0, 122, 255, .45);
  --on-accent: #fff;                     /* mới: gốc hard-code #fff ~20 chỗ */

  --bg: #F5F5F7;
  --chrome: rgba(246, 246, 248, .9);
  --side: #EBEBEF;
  --surface: #FFFFFF;
  --surface2: #F2F2F5;
  --hover: rgba(0, 0, 0, .045);
  --sel: rgba(0, 122, 255, .13);

  --text: #1D1D1F;
  --text2: #6E6E73;
  --text3: #86868B;
  --sep: rgba(0, 0, 0, .11);
  --sep2: rgba(0, 0, 0, .06);

  --green: #248A3D;   --green-bg: rgba(52, 199, 89, .16);   --green-solid: #34C759;
  --orange: #C93400;  --orange-bg: rgba(255, 149, 0, .17);  --orange-solid: #FF9500;
  --red: #C9001B;     --red-bg: rgba(255, 59, 48, .13);     --red-solid: #FF3B30;
  --purple: #8944AB;  --purple-bg: rgba(175, 82, 222, .15);
  --blue: #0066CC;    --blue-bg: rgba(0, 122, 255, .12);
  --gray: #5C5C62;    --gray-bg: rgba(120, 120, 128, .14);

  --ck1: #FFFFFF;     --ck2: #E4E4E9;     /* checkerboard ảnh trong suốt */

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, .06), 0 0 0 .5px rgba(0, 0, 0, .07);
  --shadow-md: 0 6px 18px rgba(0, 0, 0, .08), 0 0 0 .5px rgba(0, 0, 0, .08);
  --shadow-lg: 0 28px 70px rgba(0, 0, 0, .2), 0 0 0 .5px rgba(0, 0, 0, .12);
  --scrim: rgba(0, 0, 0, .38);

  --light-close: #FF5F57; --light-min: #FEBC2E; --light-max: #28C840;
  --light-idle: rgba(0, 0, 0, .14);

  --radius-sm: 6px;  --radius: 8px;  --radius-md: 10px;
  --radius-lg: 12px; --radius-xl: 14px; --radius-2xl: 16px;

  --ease: cubic-bezier(.2, .8, .2, 1);
  --spring: cubic-bezier(.34, 1.36, .64, 1);

  --titlebar-h: 52px;
  --statusbar-h: 26px;
  --sidebar-w: 248px;
  color-scheme: light;
}

[data-theme="dark"] {
  --accent: #0A84FF;
  --accent-soft: rgba(10, 132, 255, .2);
  --accent-ring: rgba(10, 132, 255, .55);
  --bg: #1C1C1E;
  --chrome: rgba(38, 38, 40, .92);
  --side: #252527;
  --surface: #2C2C2E;
  --surface2: #232325;
  --hover: rgba(255, 255, 255, .06);
  --sel: rgba(10, 132, 255, .26);
  --text: #F5F5F7;
  --text2: #B4B4BA;
  --text3: #8E8E93;
  --sep: rgba(255, 255, 255, .12);
  --sep2: rgba(255, 255, 255, .07);
  --green: #4ADE80;   --green-bg: rgba(48, 209, 88, .18);   --green-solid: #30D158;
  --orange: #FFB340;  --orange-bg: rgba(255, 159, 10, .18); --orange-solid: #FF9F0A;
  --red: #FF7A72;     --red-bg: rgba(255, 69, 58, .2);      --red-solid: #FF453A;
  --purple: #DDA0FF;  --purple-bg: rgba(191, 90, 242, .2);
  --blue: #64B0FF;    --blue-bg: rgba(10, 132, 255, .22);
  --gray: #B4B4BA;    --gray-bg: rgba(142, 142, 147, .2);
  --ck1: #3A3A3C;     --ck2: #2D2D2F;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, .3), 0 0 0 .5px rgba(255, 255, 255, .07);
  --shadow-md: 0 8px 22px rgba(0, 0, 0, .35), 0 0 0 .5px rgba(255, 255, 255, .08);
  --shadow-lg: 0 30px 80px rgba(0, 0, 0, .6), 0 0 0 .5px rgba(255, 255, 255, .1);
  --scrim: rgba(0, 0, 0, .5);
  --light-idle: rgba(255, 255, 255, .16);
  color-scheme: dark;
}
```

### Quy tắc dùng màu

| Vai trò | Token |
|---|---|
| Nền app / nền vùng content | `--bg` |
| Sidebar | `--side` |
| Card, sheet, input, button thường | `--surface` |
| Nhóm lồng trong card (settings group, stat box, log, tip) | `--surface2` |
| Hover list/button ghost | `--hover` |
| Item đang chọn (tree, tab, icon-btn on) | `--sel` nền + `--accent` chữ |
| Focus ring input | border `--accent` + `0 0 0 3px var(--accent-soft)` |
| Focus-visible chung | `outline: 3px solid var(--accent-ring)` |
| Chữ chính / phụ / mờ | `--text` / `--text2` / `--text3` |
| Đường kẻ giữa section / giữa row | `--sep` / `--sep2` |
| Trạng thái | chip/note: `--x` + `--x-bg`; dot/progress/icon trong toast: `--x-solid` |
| Toast | đảo màu: nền `--text`, chữ `--bg` |

---

## 3. Typography

Font self-host woff2, subset `vietnamese` + `latin-ext` + `latin` (xem
`src/renderer/src/assets/fonts/fonts.css`): **Be Vietnam Pro** 400/500/600/700,
**JetBrains Mono** 500. `font-display: swap`.

Body: `font: 14px/1.5 var(--font); -webkit-font-smoothing: antialiased;`

Scale chuẩn hoá (gốc có ~16 size lẻ; app mới dùng bảng này):

| Token gợi ý | Size / weight | Dùng cho |
|---|---|---|
| `display` | 64 / 700, ls -.025em, lh 1.1 | Splash title |
| `h1` | 22 / 700, ls -.01em | Tiêu đề màn (`.mhead h1`) |
| `title` | 20 / 700 | Tiêu đề editable / step title |
| `h2` | 17 / 650 | Tiêu đề section, dialog |
| `h2-sm` | 15 / 600 | Header drawer, empty state, coach bubble |
| `card-title` | 14 / 650 | Tiêu đề card |
| `body` | 14 / 400–500 | Mặc định |
| `ui` | 13 / 500–600 | Toast, menu item, crumbs, h3 (13/600) |
| `small` | 12–12.5 / 400–600 | Chip lọc, segmented, label form (12/600 `--text2`), mô tả |
| `meta` | 11.5 / 400 `--text3` | Meta card, sub-text |
| `label` | 11 / 600 `--text3`, ls .02em | Label nhóm sidebar/drawer |
| `overline` | 11 / 600 UPPERCASE, ls .04em | Tiêu đề notes |
| `mono-tag` | 10–10.5 / 600 mono | vtag, kbd, tchip, version |
| `mono` | 12 / 500 mono | Path, log (11.5/1.6), command |

Weight dùng: 400, 500, 600, 650, 700. Số luôn `font-variant-numeric: tabular-nums`.

---

## 4. Spacing, radius, elevation

**Spacing** (px): 2 · 4 · 6 · 8 · 10 · 12 · 14 · 16 · 18 · 22 · 24 · 28.
- Padding ngang vùng content: **24px** (step/editor), **28px** (gallery/home).
- Header màn `.mhead`: `22px 28px 14px`. Toolbar/footbar/step-intro: `10–12px 24px`.
- Gap grid: card lớn 18, tile 12, review 14. Gap row/control: 6–8.

**Radius** (chuẩn hoá cho app mới):

| Phần tử | Radius |
|---|---|
| Tag/kbd/vtag | 4–5 |
| Seg thumb, tree node, menu item, chip vuông | 6 (`--radius-sm`) |
| Button, icon-btn, stepper, dd | 7 |
| Input, segmented track, tip | 8 (`--radius`) |
| Menu popup, ref thumb, textarea | 9 |
| Toast, note-in-card, opt-card | 10 (`--radius-md`) |
| Tile nhỏ, settings group, banner, queue card | 11 |
| Card section (`card-s`), list job, coach hole | 12 (`--radius-lg`) |
| Card gallery, sheet/dialog | 14 (`--radius-xl`) |
| Setup card, drop overlay | 16 (`--radius-2xl`) |
| Empty drop zone, hero card | 18 |
| Pill / chip tròn | 999 hoặc = height/2 |

**Elevation**: `sm` = mọi card/button nổi; `md` = hover card, popover nổi, setup card;
`lg` = sheet, menu, drawer, toast. Không chồng thêm border khi đã có shadow (shadow chứa
viền 0.5px).

---

## 5. Base CSS

```css
* { box-sizing: border-box; }
html, body, #root { height: 100%; margin: 0; }
body {
  font: 14px/1.5 var(--font);
  color: var(--text);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
  user-select: none;
  transition: background .25s var(--ease), color .25s var(--ease);
}
button, input, textarea, select { font: inherit; color: inherit; }
button { cursor: default; }
button:disabled { cursor: not-allowed; }
:focus-visible { outline: 3px solid var(--accent-ring); outline-offset: 1px; border-radius: 6px; }
h1, h2, h3 { margin: 0; font-family: var(--display); letter-spacing: -.01em; }
h1 { font-size: 22px; font-weight: 700; }
h2 { font-size: 17px; font-weight: 650; }
h3 { font-size: 13px; font-weight: 600; }
p { margin: 0; }
.muted { color: var(--text2); }
.mono { font-family: var(--mono); font-size: 12px; }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb {
  background: var(--sep); border-radius: 10px;
  border: 3px solid transparent; background-clip: content-box;
}
::-webkit-scrollbar-track { background: transparent; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
  }
}
```

---

## 6. App shell

```
┌───────────────────────────────────────────── titlebar 52px (chrome, blur, drag) ┐
│ ● ● ●  Workspace › Project › Step                     [icon-btn] [pill] [⚙]    │
├────────────── sidebar 248px (--side) ─┬──────── main (--bg) ────────────────────┤
│ [logo] Workspace name                  │  .mhead  h1 + sub        [actions]      │
│        mono path 10.5px               │  ───────────────────────────────────    │
│ LABEL                                  │  content (grid / editor / split)        │
│  ▸ tree node 28px          count       │                                         │
│  ▸ tree node (act = --sel)            │                                         │
│ ─────────── side-foot ─────────────── │                                         │
├────────────────────────────────────────┴─────────────── statusbar 26px (11px) ──┤
│ ● Ready   ·  model chip  ·  queue ● 2 running                       © year       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

```css
.app { display: grid; grid-template-rows: var(--titlebar-h) 1fr var(--statusbar-h); height: 100vh; }
.titlebar {
  display: flex; align-items: center; gap: 10px; padding: 0 12px 0 18px;
  background: var(--chrome); border-bottom: 1px solid var(--sep);
  backdrop-filter: blur(24px); -webkit-app-region: drag; position: relative; z-index: 5;
}
.titlebar button, .titlebar input { -webkit-app-region: no-drag; }
.body { display: grid; grid-template-columns: var(--sidebar-w) 1fr; min-height: 0;
  transition: grid-template-columns .3s var(--ease); }
.body.side-off { grid-template-columns: 0 1fr; }
.side { background: var(--side); border-right: 1px solid var(--sep); overflow: hidden; }
.side-inner { width: var(--sidebar-w); }   /* giữ width cố định để collapse trượt mượt */
.main { position: relative; min-width: 0; min-height: 0; overflow: hidden; }
.view { position: absolute; inset: 0; display: flex; flex-direction: column; }
.status {
  display: flex; align-items: center; gap: 10px; padding: 0 14px;
  font-size: 11px; color: var(--text2);
  border-top: 1px solid var(--sep); background: var(--chrome);
}
```

- **Traffic lights**: 3 nút 12px tròn, gap 8, `inset 0 0 0 .5px rgba(0,0,0,.12)`; glyph chỉ hiện
  khi hover cụm; window mất focus (`.app.blurred`) → cả 3 về `--light-idle`.
- **Crumbs**: 13/600, phần mờ `--text2` 500, separator icon chevron `--text3`.
- **Tree node** `.tn`: h28, padding 0 6, radius 6, icon `--accent`, hover `--hover`, active
  `--sel` + label 600, count 11px `--text3` tabular.
- **Status dot** 7px: ok `--green-solid`, run `--accent` + pulse 1.4s, warn `--orange-solid`,
  err `--red-solid`, idle `--text3`.
- Route chuyển màn: slide ngang có hướng (xem §9). Toast, update banner, drawer neo theo
  `--titlebar-h` / `--statusbar-h`.

---

## 7. Components

### 7.1 Button

| Variant | Spec |
|---|---|
| `.btn` | h30, padding 0 13, radius 7, border 1px `--sep`, bg `--surface`, 500, gap 6, `--shadow-sm`. Hover `--surface2`. Active `scale(.97)` (spring). Disabled opacity .45, bỏ shadow |
| `.primary` | bg `--accent`, border trong suốt, chữ `--on-accent` 600. Hover `filter: brightness(1.08)` |
| `.ghost` | trong suốt, không shadow, `--text2`; hover `--hover` + `--text` |
| `.danger.solid` | bg `--red-solid`, chữ trắng, hover brightness 1.05 |
| `.sm` | h26, padding 0 10, 12px |
| `.lg` | h36, padding 0 18, 14px, radius 9 |
| `.on` (toggle) | bg `--sel`, border + chữ `--accent` |
| `.icon-btn` | 30×30, radius 7, trong suốt, `--text2`; hover `--hover`; active scale .92; `.on` = `--sel` + `--accent` |
| `.pill-btn` | h26, padding 0 9, radius 7, border `--sep`, 11px 600 ls .04em (vd "EN/VI") |

Transition chuẩn: `background .15s, transform .15s var(--spring), box-shadow .15s, opacity .15s, filter .15s`.
Spinner trong button 12px; kbd trong button 10px nền `rgba(127,127,127,.2)` (primary: `rgba(255,255,255,.25)`).

### 7.2 Form

| Control | Spec |
|---|---|
| Field wrap `.fld` | mt 14; label 12/600 `--text2`, mb 5; lỗi `.fld-err` 12px `--red` |
| Input `.inp` | h32, radius 8, border `--sep`, padding 0 10, bg `--surface`. Focus: border `--accent` + ring 3px `--accent-soft`. Transition .15s |
| Textarea `.ta` | radius 9, padding 9 11, lh 1.5, resize vertical, placeholder `--text3`, focus như input |
| Dropdown nhỏ `.dd` | h28 (sm 26), radius 7, 12.5px, max-w 190 |
| Search | h30, radius 8, bg `--gray-bg` (không border), w220; focus-within ring `--accent-soft`; nút xoá 18px tròn bg `--sep` |
| Inline title | 20/700, trong suốt; hover hiện border `--sep`; focus như input |
| Numeric stepper | inline-flex, border `--sep`, radius 7; nút 28×26 15px `--text2`; output min-w 26, 600 tabular; số đổi có animation trượt dọc (§9) |
| Switch | track 34×20 radius 10 `--gray-bg`; knob 16px trắng, `0 1px 3px rgba(0,0,0,.25)`; on: track `--green-solid`, knob `translateX(14px)` `.22s var(--spring)` |
| Checkbox overlay (trên tile) | 20px radius 6, border 1.5px `rgba(0,0,0,.25)`, bg trắng .92; ẩn, hiện khi hover/selected; checked = `--accent` + check trắng |
| Native checkbox | `accent-color: var(--accent)`, 15×15 |
| Radio badge (trên card) | 22px tròn góc trên-phải, bg trắng .88, ring 1.5px `rgba(0,0,0,.18)`; chọn = `--accent` |

Control heights chuẩn hoá: **24** (chip/kc/mchip) · **26** (sm, seg item, filter chip) ·
**30** (btn, icon-btn, search) · **32** (input) · **36** (btn lg).

### 7.3 Segmented control

```css
.seg { display: inline-flex; padding: 2px; gap: 2px; border-radius: 8px; background: var(--gray-bg); }
.seg button { position: relative; height: 24px; padding: 0 10px; border: 0; border-radius: 6px;
  background: transparent; color: var(--text2); font-size: 12px; font-weight: 500; transition: color .18s; }
.seg button.on { color: var(--text); font-weight: 600; }
.seg .seg-thumb { position: absolute; inset: 0; border-radius: 6px; background: var(--surface); box-shadow: var(--shadow-sm); }
.seg .seg-label { position: relative; }
```
Thumb trượt bằng `motion` `layoutId` (spring 520/38). `role="radiogroup"` + `role="radio"`.

### 7.4 Chip / tag / badge

- `.chip`: h20, padding 0 7, radius 10, 11/600; màu `c-{gray|blue|green|orange|red|purple}` =
  `color: var(--x); background: var(--x-bg)`.
- Filter chip `.fchip`: h26, pill, border `--sep`, bg `--surface`, 12/500 `--text2`; **on = đảo
  màu** (bg `--text`, chữ `--bg`); count trong `<b>` 600 `--text3`.
- Model chip `.mchip`: h24, radius 6, `--gray-bg`, mono 500 11.5px.
- Tag mono `.vtag`: mono 600 10px/1, padding 3 5, radius 4, `--gray-bg`.
- `kbd`: mono 600 10.5px, padding 3 6, radius 5, `--surface2` + ring 1px `--sep`.
- Changelog label: pill 10.5/600 — update=blue, add=green, remove=gray, fix=orange.

### 7.5 Card / tile

| Loại | Spec |
|---|---|
| Gallery card `.card` | bg `--surface`, radius 14, `--shadow-sm`, overflow hidden. Hover `translate: 0 -3px` + `--shadow-md`; active -1px. Transition `.25s var(--ease)`. Thumb 16:9 trên nền checker, padding 12, lưới 2×2 gap 6 (`object-fit: scale-down`); body padding `12 14 14`; title 14/650 ellipsis; meta 11.5 `--text3`; row 12 `--text2` tabular |
| Section card `.card-s` | `--surface`, radius 12, `--shadow-sm`, padding 16 |
| Tile `.tile` | radius 11, padding 8, `--shadow-sm`; thumb 4:3 radius 7; name 12/600 mt 7; hover -2px + md. **Selected** = `0 0 0 2px var(--accent)` + md + badge check 18px góc (anim `pop .3s spring`) |
| Option card `.tpl/.sg` | radius 13, border 1.5px `--sep2`, bg `--surface2`; hover -2px; **on** = border `--accent` + ring 4px `--accent-soft`; **locked/xác nhận** = border `--green-solid` + ring 4px `--green-bg` |
| List item `.gitem` | radius 11, padding 10 12, border 1px trong suốt; hover `translateX(2px)`; on = border accent + ring 3px soft |
| Nested box (stat, queue card, tip, log) | `--surface2`, radius 10–11, padding 10–12, không shadow |
| Hero/setup card | `--surface`, radius 16, `--shadow-md`, padding `28 28 20`, w min(720px,100%) |

**Selected state chuẩn hoá** cho app mới (gốc lẫn 5 kiểu):
1. Card/tile chọn được → ring accent (2px tile, 3–4px card có border) + `--accent-soft` halo.
2. Item trong list/tree/tab → nền `--sel` + chữ `--accent`.
3. Segmented/pill nhóm → thumb `--surface` + `--shadow-sm`.
4. Filter chip → đảo màu.

**Grid**: `grid-template-columns: repeat(auto-fill, minmax(<min>, 1fr))` — card 250/gap 18,
review 210/gap 14, option 150–250/gap 12–14, tile 148/gap 12, picker 124/gap 10.

**Checkerboard** cho ảnh trong suốt:
```css
.ck { background: conic-gradient(var(--ck1) 25%, var(--ck2) 0 50%, var(--ck1) 0 75%, var(--ck2) 0) 0 0 / 14px 14px; }
```

### 7.6 Workflow stepper (thanh bước)

- Container: padding `14 24 12`, border-bottom `--sep2`, bg `--surface`.
- Step: padding `6 12 6 8`, radius 10, hover `--hover`; số 24px tròn `--gray-bg` 650/12;
  **done** = `--green-bg`/`--green`; **current** = `--accent` nền + trắng, `scale(1.08)`
  (spring .25s); **locked** opacity .5, not-allowed. Nhãn 13/600 + small 11 `--text3`.
- Connector 2px `--sep`, fill `--green-solid` chạy `scaleX` .45s ease.
- Dưới stepper có **step intro** (padding 10 24): icon 16 + "Bước n/N · Tên" 13/600 accent +
  mô tả + "→ bước tiếp" 12/500.

### 7.7 Dialog / sheet

```css
.modal-root { position: fixed; inset: 0; z-index: 50; display: grid; place-items: center; }
.scrim { position: absolute; inset: 0; background: var(--scrim); backdrop-filter: blur(2px); }
.sheet { position: relative; background: var(--surface); border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg); display: flex; flex-direction: column; max-height: calc(100vh - 60px); }
.dlg { width: min(460px, calc(100vw - 40px)); padding: 22px; overflow: auto; }
.dlg.wide { width: min(640px, calc(100vw - 40px)); }
.dlg h2 { display: flex; align-items: center; gap: 10px; }
.dlg .dlg-ic { width: 40px; height: 40px; border-radius: 11px; display: grid; place-items: center;
  background: var(--accent-soft); color: var(--accent); flex: none; }
.dlg .dlg-ic.warn { background: var(--orange-bg); color: var(--orange); }
.dlg .dlg-ic.danger { background: var(--red-bg); color: var(--red); }
.dlg p { color: var(--text2); margin: 12px 0 0; }
.dlg .acts { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
```
- Esc đóng, click scrim đóng, autofocus sheet (`tabIndex=-1`), `role="dialog"|"alertdialog"`,
  `aria-modal`, `aria-label`.
- Kích thước khác: picker `min(860px)×min(640px)`, lightbox `min(1100px)`, review sheet gần
  full-screen (cách titlebar, w `calc(100%-40px)`).
- **Settings dialog** kiểu System Settings: 720×560, header tab dạng icon-trên-chữ (`.stab`
  min-w 76, 11.5/500, on = `--sel` + accent), body padding `18 26 22`, nội dung chia **group**
  (`--surface2`, radius 11, padding 2 14) gồm **row** min-h 46, border-bottom `--sep2`.

### 7.8 Drawer

Fixed phải, `top: var(--titlebar-h); bottom: var(--statusbar-h)`, w 380, `--surface`,
`--shadow-lg`, border-left `--sep`, z 40. Header padding `12 14 12 16` (h2 15px), body `14 16`
gap 10, footer `10 16` border-top `--sep2`. Label 11/600 `--text3` ls .02em.

### 7.9 Context menu

Fixed, min-w 200 / max-w 320, `--surface`, radius 9, `--shadow-lg`, padding 5, z 80,
`transform-origin: top left`. Item: padding 6 10, radius 6, 13px, gap 8; **hover/focus = nền
`--accent` + chữ trắng** (kiểu menu macOS); `.danger` chữ `--red`, hover nền `--red-solid`.
Separator `hr` 1px `--sep2`, margin 4 2. App mới: thêm exit animation (gốc thiếu).

### 7.10 Toast

Stack giữa đáy, `bottom: calc(var(--statusbar-h) + 18px)`, gap 8, z 90, tối đa 4.
Toast: padding 9 14, radius 10, **nền `--text` chữ `--bg`**, 13/500, `--shadow-lg`,
max-w `min(620px, 100vw - 60px)`, text clamp 2 dòng. Icon 15px màu solid theo kind
(ok/info/warn/err). Click để tắt. Tự tắt: ok/info 3.2s, warn/err 6s.

### 7.11 Banner / note

- Note inline: flex gap, padding 10 14, radius 11; mặc định `--accent-soft`; `.warn`
  orange, `.err` red, `.info` blue (cặp text + bg).
- Quota/pause banner: padding 12 14, radius 11, countdown mono 700 18px.
- Lockbar (dải xác nhận dưới editor): padding 10 24, border-top `--sep2`; trạng thái đã khoá →
  `--green-bg`.
- Update banner nổi góc phải-dưới: w360, radius 14, nền `--chrome` + `blur(24px)
  saturate(180%)`, `--shadow-lg`, anim `upd-in .32s spring`.

### 7.12 Progress / loading

- Bar: h6 radius 3 `--gray-bg`, fill `--accent` `width .35s var(--ease)`; `.big` h8;
  `.green/.warn/.err` đổi fill sang solid; `.indeterminate` fill 40% chạy `slide 1.2s`.
- Spinner: 15px, border 2px `--accent-soft`, top `--accent`, `spin .8s linear` (xs 9, btn 12, lg 36).
- Skeleton: gradient shimmer 1.3s, radius 13, aspect 4:3.
- Job dots: mỗi bước 14×5 radius 3; done green, current accent + pulse 1.1s, fail red.
- Big result icon: 72px tròn solid green/orange, `pop .5s spring`.

### 7.13 Empty state & drop zone

- `.empty`: center, padding 70 20, icon `--text3`, h3 15px `--text`, mô tả `--text2`,
  actions gap 8 mt 12.
- `.empty-drop`: border 2px dashed `--sep`, radius 18, padding 40, icon `--accent`, p max-w 420.
- Drag-over overlay: inset 10, radius 16, 2px dashed `--accent`, nền
  `color-mix(in srgb, var(--accent) 9%, var(--bg))`.
- Chặn drop file toàn cục (window dragover/drop `dropEffect='none'`), chỉ vùng drop nhận.

### 7.14 Coach marks (onboarding tour)

Lỗ highlight radius 12 tạo bằng `box-shadow: 0 0 0 9999px rgba(0,0,0,.5), 0 0 0 3px
var(--accent), 0 0 0 7px var(--accent-soft)` (dark .62); di chuyển `.38s var(--ease)`.
Bubble w304, radius 12, `--shadow-lg`, padding 16; kicker 11/600 accent; h3 15/600; dots 6px
(on = 16px accent, done = `--accent-ring`). Mỗi tour chạy 1 lần, có replay trong settings.

### 7.15 Splash

Full-screen `--bg`, logo 128 (spring scale + rotate từ -28°, ring lan toả, shine quét), title
64/700 hiện từng chữ (y 22 + blur 8 → 0, stagger .06s), tagline 15 `--text2`, progress 180×3,
copyright 12 `--text3` góc phải. Giữ ~3.9s, click để bỏ qua.

---

## 8. Iconography

- SVG inline, `viewBox 0 0 24 24`, `fill="none"`, `stroke="currentColor"`,
  **`strokeWidth 1.8`**, `round` cap/join, `aria-hidden`. Size mặc định 16 (12 / 15 / 16 / 20 /
  28–40 cho hero).
- Component: `<Icon name size className />`, map `PATHS` một file
  (`src/renderer/src/components/Icon.tsx` — copy được nguyên).
- Bộ hiện có: folder plus x check gear sun moon chev right left up shield grid sidebar box
  terminal sparkles refresh alert clock user logout download upload help external cloud search
  image lock unlock more trash edit layers file eye link sort folderPlus pause play queue copy
  palette save flag wand.
- Màu icon theo ngữ cảnh: `--text2` mặc định, `--accent` cho icon điều hướng/nhấn mạnh,
  `--text3` cho icon trang trí/empty.

---

## 9. Motion

Lib: `motion` (`motion/react`). Bọc app trong `<MotionConfig reducedMotion="user">`.

```ts
export const EASE: [number, number, number, number] = [0.2, 0.8, 0.2, 1]
export const viewTransition: Transition = { duration: 0.26, ease: EASE }
export const fadeTransition: Transition = { duration: 0.2, ease: EASE }
export const sheetTransition: Transition = { type: 'spring', stiffness: 420, damping: 32, mass: 0.9 }
export const thumbTransition: Transition = { type: 'spring', stiffness: 520, damping: 38 }
```

| Pattern | initial → animate → exit | Transition |
|---|---|---|
| Route / step (có hướng `d=±1`) | `{opacity 0, x 14d}` → `{1, 0}` → `{0, x -10d}` | view |
| Modal panel | `{opacity 0, y 16, scale .97}` → rest → `{0, y 8, scale .98}` (exit dùng fade) | sheet |
| Scrim | opacity 0 ↔ 1 | fade |
| Toast | `{0, y 14, scale .96}` → rest → `{0, y 6, scale .98, .18s}`, `layout` | sheet |
| Drawer | `{x 400, opacity .6}` → `{0, 1}` → `{x 400, 0, .22s}` | sheet |
| Menu | `{0, scale .96, y -4}` → rest | fade |
| Banner | y -6 ↔ 0 | fade |
| Segmented thumb | `layoutId` | thumb |
| Số đổi (stepper) | mới `y -6 → 0`, cũ `→ y 6`, `mode="popLayout"` | fade |
| Card list vào | `{y 8–10, scale .985}` → rest, .28–.32s, stagger `min(i, 12–24) × .015–.035s` | EASE |
| Ảnh load | scale .92–.97 → 1, .3–.4s | EASE |
| Swap nội dung cùng chỗ | `AnimatePresence mode="wait"`, opacity + x/y ≤10 | fade |

CSS: hover/press dùng `var(--spring)` cho transform, `var(--ease)` cho layout/shadow.
Keyframes: `pop` (.6 → 1.12 → 1), `fadeUp` (y 6), `imgIn` (scale .97), `slide`, `spin`,
`pulse`/`gas-pulse` (opacity → .35–.45), `gas-shimmer` (background-position 200% → -200%).

Nguyên tắc: biên độ nhỏ (≤16px, scale ≥ .96), exit nhanh hơn enter, stagger có trần index,
press feedback scale .92–.98.

---

## 10. Layout patterns màn hình

| Pattern | Grid |
|---|---|
| Gallery / home | `.mhead` + grid card auto-fill 250 |
| Editor 2 cột | `minmax(0,1fr) 340px` (≤1240 → 300px), side panel border-left `--sep2` |
| Split 3 cột (list – content – inspector) | `210px 1fr 290px` |
| Review | `minmax(0,1fr) 340px` inspector (≤1180 → 300) |
| Export | `minmax(0,1.2fr) minmax(0,1fr)` gap 16 (≤980 → 1 cột) |
| Form hẹp / config | max-w 800 center |
| Setup / onboarding | card 720 center, padding 40 24 |
| Job table | grid cột cố định, row padding 9 14, border-bottom `--sep2` |

Breakpoints: 1240 / 1180 / 980 (desktop-only, min window ~960).

---

## 11. Accessibility & i18n

- Focus-visible ring 3px `--accent-ring` cho mọi control; trong coach bubble 2px offset 2.
- Segmented = radiogroup; dialog có `aria-modal`; toast container `role="status" aria-live="polite"`.
- Disabled: opacity .35–.55 + `cursor: not-allowed`.
- Text tiếng Việt: font có subset vietnamese, tránh `text-transform: uppercase` trên câu dài
  (chỉ dùng cho overline ngắn).
- i18next + react-i18next; mọi string qua `t()`; chừa chỗ cho chuỗi dài hơn (ellipsis +
  `title` tooltip).

---

## 12. Cải tiến nên áp ngay khi port sang app mới

Những điểm gốc chưa đồng nhất — app mới làm sạch từ đầu:

1. Thêm `--on-accent` thay `#fff` hard-code; thêm `--overlay-chip` (`rgba(0,0,0,.5)`) cho label
   trên ảnh; checker dark dùng `--ck1/--ck2` thay hex riêng.
2. Chốt 1 scale radius (bảng §4) và 1 scale control height (§7.2).
3. Chốt 4 kiểu selected (§7.5), không thêm kiểu mới.
4. Hover lift thống nhất: tile/card nhỏ -2px, card lớn -3px.
5. Typography theo bảng §3, bỏ size lẻ (9, 12.5, 13.5, 19).
6. Context menu có exit animation (`AnimatePresence`).
7. Gom component thành thư viện: `Button, IconButton, Input, Textarea, Select, Search, Switch,
   Checkbox, Segmented, Stepper, Chip, Card, Tile, Modal, Drawer, Menu, Toast, Note, Banner,
   Progress, Spinner, Skeleton, EmptyState, DropZone, StepBar, Icon`.

---

## 13. Checklist triển khai

1. Copy font woff2 + `fonts.css`, tạo `tokens.css` (§2) + `base.css` (§5).
2. Theme store: setting `system|light|dark`, lắng nghe OS theme, set `data-theme` trước khi
   render (tránh flash).
3. Dựng shell (§6): titlebar frameless + traffic lights, sidebar collapse, statusbar.
4. `lib/motion.ts` (§9) + `MotionConfig reducedMotion="user"`.
5. `Icon.tsx` (§8).
6. Component lib (§7) theo thứ tự: Button → Input/Form → Segmented → Chip → Card/Tile →
   Modal → Toast → Menu → Drawer → Progress/Empty.
7. Kiểm cả light + dark, reduced motion, cửa sổ 960px và full HD.
