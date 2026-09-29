# Project G — Design Specification
## Inspired by HoYoverse / Genshin Impact visual design principles

> Mục tiêu: chuyển các đặc trưng thị giác đã phân tích từ Genshin Impact thành một hệ thống thiết kế có thể áp dụng cho Project G.
>
> Đây không phải bản sao UI Genshin. Hệ thống ưu tiên tái sử dụng các nguyên tắc: silhouette rõ, phân cấp thị giác mạnh, fantasy ornament có kiểm soát, màu theo ngữ nghĩa, giao diện nhẹ khi thao tác chính và giàu chất liệu hơn khi người dùng đi sâu vào nội dung.

---

# 1. Design Direction

Project G sử dụng phong cách:

**Stylized anime-fantasy desktop UI + lightweight glass surfaces + restrained ornamental details.**

Ba mục tiêu chính:

1. **Readable first**  
   Người dùng phải hiểu ngay hành động chính, trạng thái hiện tại và bước tiếp theo.

2. **World-first, UI-second**  
   Artwork nhân vật, icon vật phẩm và thông tin game là phần tạo cảm xúc. UI đóng vai trò khung hỗ trợ, không cạnh tranh sự chú ý.

3. **Controlled variance**  
   Hệ thống tổng thể giữ cùng typography, spacing, shape language và component behavior, trong khi nhân vật, nguyên tố và vùng có thể thay đổi accent, illustration và motif.

---

# 2. Core Visual Principles

## 2.1 Recognition at a glance

Mọi thành phần quan trọng phải nhận diện được trước khi đọc chữ.

Ưu tiên:

- silhouette rõ;
- icon có hình dáng khác nhau;
- màu chỉ là lớp nhận diện thứ hai;
- hình ảnh nhân vật có crop dễ nhận biết;
- trạng thái chính có contrast mạnh hơn trạng thái phụ.

Không phụ thuộc duy nhất vào màu sắc để phân biệt state.

---

## 2.2 Large forms before detail

Thứ tự đọc:

**primary action → subject → progress/state → supporting detail → metadata**

Tránh để decoration, border hoặc effect nhỏ cạnh tranh với nội dung chính.

Mỗi màn hình nên có tối đa một visual anchor chính.

---

## 2.3 Ornament only where attention slows down

### Main workflow
Ornament rất nhẹ.

Dùng:

- glass panel;
- separator mảnh;
- soft highlight;
- small gold accent;
- subtle elemental glow.

### Detail / modal / character page
Có thể tăng ornament:

- frame fantasy mảnh;
- radial motif;
- decorative corner;
- layered illustration;
- embossed / luminous accent.

Nguyên tắc:

> Người dùng càng tập trung vào thao tác nhanh, UI càng ít trang trí.

---

# 3. Shape Language

## 3.1 Base geometry

Primary shape:

- rounded rectangle;
- soft capsule;
- circle;
- thin arc;
- radial indicator.

Không sử dụng các khối vuông cứng dày đặc.

### Corner radius

| Token | Value | Use |
|---|---:|---|
| `radius-xs` | 6 px | chip nhỏ, tooltip |
| `radius-sm` | 10 px | input, control |
| `radius-md` | 14 px | card |
| `radius-lg` | 20 px | large panel |
| `radius-xl` | 28 px | hero surface |
| `radius-pill` | 999 px | status pill |

---

## 3.2 Border language

Border:

- 1 px;
- low contrast;
- sáng hơn nền một chút;
- tránh border đen nặng.

Accent border chỉ dùng cho:

- selected;
- active;
- pinned;
- critical recommendation.

Không dùng border ở mọi layer.

---

# 4. Color System

Không dùng một palette cố định cho toàn bộ nội dung game.

Hệ thống gồm hai lớp:

**Global UI palette + contextual accent palette**

---

## 4.1 Global dark palette

```text
bg-canvas           #0C1018
bg-elevated         #121824
bg-panel            rgba(24, 32, 46, 0.72)
bg-panel-strong     rgba(28, 38, 54, 0.88)

text-primary        #F3F5F7
text-secondary      #B9C0CB
text-muted          #7F8998

stroke-soft         rgba(255,255,255,0.08)
stroke-medium       rgba(255,255,255,0.14)

gold-soft           #D9C28B
gold-highlight      #F0D89C
```

---

## 4.2 Global light palette

```text
bg-canvas           #F3F1EA
bg-elevated         #FAF9F5
bg-panel            rgba(255,255,255,0.72)
bg-panel-strong     rgba(255,255,255,0.90)

text-primary        #262A31
text-secondary      #626A76
text-muted          #9199A4

stroke-soft         rgba(38,42,49,0.08)
stroke-medium       rgba(38,42,49,0.14)

gold-soft           #A88A52
gold-highlight      #C5A35F
```

---

## 4.3 Elemental accents

Elemental colors không được phủ toàn bộ UI.

Dùng cho:

- icon;
- glow;
- progress;
- selected outline;
- mini badge;
- visual anchor.

```text
Anemo    #65D5C5
Geo      #E4B45D
Electro  #A778E8
Dendro   #8FC65C
Hydro    #60AEEF
Pyro     #F06A58
Cryo     #89D6EB
```

Accent phải được desaturate hoặc giảm opacity khi dùng trên surface lớn.

---

# 5. Surface & Glass

Project G dùng glass theo hướng tinh tế, không phải glassmorphism phô trương.

## Standard glass panel

```text
background:
  rgba(20, 27, 39, 0.68)

backdrop blur:
  18–28 px

border:
  1 px rgba(255,255,255,0.08)

shadow:
  0 16px 48px rgba(0,0,0,0.20)
```

Không stack quá 3 lớp translucent lên nhau.

Nếu card nằm trên glass panel, card con nên dùng:

- opaque nhẹ;
- hoặc contrast bằng luminance;

thay vì blur tiếp.

---

# 6. Typography

Typography phải thanh, sạch và ít mang cảm giác dashboard kỹ thuật.

## Hierarchy

| Role | Size | Weight |
|---|---:|---:|
| Display | 30–36 px | 600 |
| Page title | 24–28 px | 600 |
| Section title | 18–20 px | 600 |
| Card title | 15–17 px | 600 |
| Body | 14–15 px | 400 |
| Label | 12–13 px | 500 |
| Metadata | 11–12 px | 400 |

Không dùng quá 3 cấp typography trong một card.

### Rules

- heading ngắn;
- sentence case;
- tránh ALL CAPS;
- line-height thoáng;
- số liệu quan trọng dùng tabular numerals nếu font hỗ trợ.

---

# 7. Spacing System

Base unit: **4 px**

```text
space-1   4
space-2   8
space-3   12
space-4   16
space-5   20
space-6   24
space-8   32
space-10  40
space-12  48
space-16  64
```

Default card padding:

**20–24 px**

Default gap giữa các section:

**28–40 px**

Khoảng trắng phải được coi là một thành phần thiết kế, không phải vùng cần lấp đầy.

---

# 8. Layout

## 8.1 Main application shell

Khuyến nghị:

```text
┌──────────────────────────────────────────────┐
│ compact navigation                          │
├───────────────┬──────────────────────────────┤
│ sidebar       │ main content                 │
│ optional      │                              │
│               │ primary recommendation       │
│               │                              │
│               │ supporting information       │
└───────────────┴──────────────────────────────┘
```

Sidebar chỉ xuất hiện khi thực sự cần.

Không tạo nhiều panel ngang hàng có trọng số giống nhau.

---

## 8.2 Content width

Desktop:

```text
content max-width: 1180–1320 px
```

Main task column:

```text
680–840 px
```

Secondary contextual column:

```text
280–360 px
```

---

# 9. Visual Hierarchy

Mỗi màn hình phải trả lời theo thứ tự:

1. **Tôi đang ở đâu?**
2. **Ứng dụng khuyên tôi làm gì?**
3. **Vì sao?**
4. **Tôi cần gì?**
5. **Có lựa chọn khác không?**

Nếu một màn hình không trả lời được 1–2 trong vòng vài giây, hierarchy chưa đạt.

---

# 10. Primary Recommendation Pattern

Đây là component quan trọng nhất của Project G.

## Hero Recommendation Card

Cấu trúc:

```text
[character artwork]

Kazuha
Nâng Thiên Phú

Lv. 8 → Lv. 9

[Primary action]

────────────────

Cần:
material chips

Nhựa dự kiến
40

Có thể farm hôm nay
Yes

[Vì sao đề xuất]
```

### Hero rules

Hero phải có:

- một nhân vật;
- một hành động;
- một mốc hiện tại;
- một mốc tiếp theo;
- một CTA chính.

Không đặt nhiều CTA ngang cấp trong hero.

---

# 11. Character Presentation

Ảnh nhân vật đóng vai trò visual identity.

## Crop rules

Ưu tiên:

- mặt;
- tóc;
- upper silhouette;
- signature accessory.

Không crop ở vị trí khiến nhân vật mất đặc trưng.

Background của portrait có thể sử dụng:

- gradient nguyên tố;
- radial glow;
- abstract motif;
- blurred splash art.

Không dùng artwork full-detail làm background trực tiếp phía sau text dài.

---

# 12. Cards

Card chỉ tồn tại nếu nó gom một nhóm thông tin có cùng mục đích.

Các loại card chính:

- Recommendation card
- Character card
- Material card
- Progress card
- Source/Farm card
- Alternative card

Không tạo generic card cho từng dòng dữ liệu.

---

# 13. Character Card

```text
┌────────────────────────────┐
│ portrait      Name         │
│               Lv. 90       │
│                            │
│ Tier / priority            │
│ progress                   │
│                            │
│ next recommended action    │
└────────────────────────────┘
```

At-a-glance information:

- portrait;
- name;
- level;
- priority;
- current target.

Chi tiết sâu chỉ hiện khi mở card.

---

# 14. Progress Visualization

Progress phải thể hiện cả:

**current state + destination**

Ví dụ:

```text
Talent
8 ━━━━━━━●━━━━ 10
          ↑
         next
```

Không chỉ hiển thị `%`.

Ưu tiên domain value thật:

- Lv. 80 → 90
- Talent 8 → 9
- Weapon 70 → 80

---

# 15. Material Presentation

Material icon phải được coi là hình ảnh gameplay, không phải icon phụ.

Một material item gồm:

```text
[icon]
12 / 18
```

Không cần hiển thị tên liên tục nếu icon đã quen thuộc và tooltip có thể cung cấp tên.

Nếu thiếu:

```text
12 / 18
      ↑ thiếu 6
```

Màu thiếu phải rõ nhưng không dùng red toàn bộ card.

---

# 16. Iconography

Icon có ưu tiên:

1. silhouette;
2. meaning;
3. stylistic consistency;
4. color.

Style:

- thin-to-medium stroke;
- rounded joins;
- geometric;
- fantasy detail rất nhẹ.

Không trộn:

- filled Material Icons;
- Lucide;
- icon game;
- emoji;

trong cùng một cấp hierarchy.

---

# 17. Navigation

Navigation nên dùng ít mục.

Đề xuất:

```text
Tiếp theo
Nhân vật
Kế hoạch
Dữ liệu
```

Settings nằm ngoài primary navigation.

Current page:

- subtle glow;
- brighter label;
- indicator nhỏ.

Không dùng large filled tab cho mọi mục.

---

# 18. Inputs

Project G không nên bắt người dùng cấu hình planner trước khi nhận kết quả.

Flow:

```text
Import data
→ Analyze
→ Recommendation
→ Optional refinement
```

Advanced controls chỉ xuất hiện sau khi hệ thống đã đưa ra kết quả có ích.

---

# 19. Buttons

## Primary

Một màn hình chỉ có một primary action nổi bật.

```text
height: 40–44 px
radius: 10–12 px
weight: 600
```

Không cần gradient mạnh.

Có thể dùng:

- luminous edge;
- subtle elemental accent;
- soft gold highlight.

## Secondary

Neutral glass / low-contrast fill.

## Tertiary

Text only.

---

# 20. Empty States

Không dùng empty state kỹ thuật như:

> No account data found.

Thay bằng instruction trực tiếp:

```text
Chưa có dữ liệu tài khoản

Nhập Account Snapshot hoặc file GOOD để Project G
phân tích nhân vật và đề xuất bước nâng cấp tiếp theo.

[Nhập dữ liệu]
```

Có thể kèm illustration đơn giản.

---

# 21. Tooltips & Progressive Disclosure

Thông tin game phức tạp nên được phân tầng.

Default:

```text
Tên
Giá trị
State
```

Hover / expand:

```text
Giải thích
Nguồn
Rule
Calculation
```

Không để engine logic chiếm UI chính.

---

# 22. Motion

Animation đóng vai trò:

- xác nhận state;
- dẫn mắt;
- tăng cảm giác chất lượng.

Không dùng animation chỉ để trang trí.

## Durations

```text
micro feedback     100–160 ms
component change   180–240 ms
panel transition   240–320 ms
hero transition    320–420 ms
```

## Easing

Ưu tiên:

```text
ease-out
cubic-bezier(0.2, 0.8, 0.2, 1)
```

---

# 23. Recommended Motion Grammar

### Hover

- translateY: -1 hoặc -2 px;
- slight luminance increase;
- border highlight.

### Selection

- border / glow tăng;
- scale không quá 1.01.

### Recommendation update

Dùng:

```text
fade
+
small vertical slide
```

Không dùng bounce.

---

# 24. Elemental Motion

Elemental identity có thể xuất hiện ở micro motion.

Ví dụ:

- Anemo → drift nhẹ;
- Hydro → ripple;
- Electro → short pulse;
- Pyro → ember-like glow;
- Cryo → crystalline shimmer;
- Dendro → soft growth arc;
- Geo → stable radial expansion.

Các effect này phải rất nhỏ trong UI.

---

# 25. Lighting & Glow

Glow chỉ dành cho:

- hero;
- selected state;
- elemental state;
- important feedback.

Không glow mọi card.

Glow radius lớn nhưng opacity thấp.

Ví dụ:

```text
0 0 32px rgba(elementColor, 0.18)
```

---

# 26. Background

Background không nên là flat #000.

Có thể dùng:

- dark blue-gray;
- subtle radial light;
- low-frequency gradient;
- blurred character/world artwork;
- subtle noise.

Noise phải gần như không nhận thấy.

---

# 27. Depth Model

Chỉ dùng khoảng 4 elevation levels:

```text
0 Canvas
1 Embedded surface
2 Card
3 Modal / floating panel
```

Không tạo quá nhiều shadow tier.

Depth chủ yếu đến từ:

- luminance;
- blur;
- overlap;
- spacing;

không phải heavy drop shadow.

---

# 28. Information Density

Project G không nên trình bày toàn bộ planner state cùng lúc.

Một màn hình chính chỉ cần:

```text
Recommendation
Current target
Required materials
Availability
Reason
Alternative
```

Các dữ liệu còn lại đưa vào:

- drawer;
- detail page;
- tooltip;
- expandable section.

---

# 29. Data Visualization

Chart chỉ dùng khi giúp người dùng ra quyết định.

Tránh:

- dashboard chart chỉ để nhìn “pro”;
- pie chart;
- gauge decoration.

Ưu tiên:

- progress line;
- timeline;
- stacked resource requirement;
- ranked list;
- compact comparison.

---

# 30. Region & Character Theming

Project G có thể đổi accent dựa trên content nhưng không đổi layout.

Ví dụ:

```text
Fontaine character
→ Hydro blue accent
→ ivory / gold local decorative hint

Inazuma character
→ Electro violet accent

Sumeru character
→ Dendro green accent
```

Typography, spacing và card geometry vẫn giữ nguyên.

Đây là nguyên tắc:

**stable system + contextual skin**

---

# 31. Accessibility

Minimum requirements:

- text contrast WCAG AA khi có thể;
- state không phụ thuộc màu;
- keyboard navigation;
- focus ring rõ;
- scalable font;
- reduced motion;
- tooltip không bắt buộc hover;
- icon quan trọng có accessible label.

---

# 32. Focus State

Focus ring:

```text
2 px
accent color
offset 2 px
```

Không loại bỏ focus outline mà không thay thế.

---

# 33. Copywriting

Copy phải giống lời hướng dẫn, không giống log hệ thống.

Không dùng:

```text
Planner resolved candidate.
Resource condition insufficient.
```

Dùng:

```text
Ưu tiên nâng Kỹ Năng Nguyên Tố của Furina lên cấp 9.

Bạn còn thiếu 6 nguyên liệu.
```

---

# 34. Main Screen — “Tiếp theo”

Mục tiêu duy nhất:

> Người dùng mở app và biết việc nên làm tiếp theo.

Layout đề xuất:

```text
Page title
↓
Hero recommendation
↓
Required materials
↓
Farm availability
↓
Why this
↓
Alternative
```

Không đặt toàn bộ roster ở trang này.

---

# 35. Character Screen

Mục tiêu:

> Xem trạng thái account và điều chỉnh ưu tiên.

Layout:

```text
Search / filter
↓
Character grid/list
↓
Selected character detail
```

Filter mặc định tối giản.

Advanced filter ẩn trong secondary control.

---

# 36. Plan Screen

Mục tiêu:

> Hiểu chuỗi hành động mà planner đề xuất.

Dùng timeline:

```text
Now
│
├─ Furina talent 8 → 9
│
├─ Weapon 80 → 90
│
├─ Kazuha talent 8 → 9
│
└─ ...
```

Không trình bày như spreadsheet nếu không cần.

---

# 37. Data Screen

Mục tiêu:

> Quản lý nguồn dữ liệu, không quản lý game inventory.

Nội dung:

```text
Current account snapshot
Last imported
Source
Import again
Validation status
```

Không biến đây thành inventory browser.

---

# 38. Component States

Mỗi interactive component tối thiểu có:

```text
default
hover
pressed
focus
selected
disabled
loading
error
```

State phải được thiết kế, không để framework tự quyết định.

---

# 39. Loading

Không dùng spinner lớn nếu hệ thống có thể hiển thị structure.

Ưu tiên skeleton:

```text
portrait placeholder
title line
progress line
material chips
```

Planner có thể dùng text:

```text
Đang phân tích tiến trình...
```

---

# 40. Success Feedback

Success state ngắn.

Ví dụ:

```text
Đã cập nhật dữ liệu.
```

Không cần modal cho action nhỏ.

---

# 41. Error Feedback

Error gồm:

1. điều gì xảy ra;
2. ảnh hưởng;
3. người dùng làm gì tiếp theo.

Ví dụ:

```text
Không đọc được file GOOD.

File không chứa dữ liệu nhân vật hợp lệ.
Hãy xuất lại file rồi thử nhập lần nữa.
```

---

# 42. Do

- dùng artwork như focal point;
- giữ HUD/interface nhẹ;
- tạo hierarchy bằng size + spacing;
- để accent phản ánh game content;
- dùng icon silhouette rõ;
- tăng ornament trong detail view;
- dùng glass có kiểm soát;
- giữ một primary action;
- dùng motion để dẫn mắt;
- giữ regional/elemental identity ở lớp contextual.

---

# 43. Don't

- không copy trực tiếp Genshin UI;
- không phủ gold ornament lên mọi thứ;
- không dùng glass trên glass quá nhiều;
- không dùng gradient neon dày đặc;
- không biến app thành analytics dashboard;
- không đặt 5 card ngang cấp trong màn hình đầu;
- không phụ thuộc hoàn toàn vào màu nguyên tố;
- không expose engine terminology mặc định;
- không bắt người dùng cấu hình trước khi nhận giá trị;
- không dùng chart nếu text/progress bar truyền đạt tốt hơn.

---

# 44. Visual Formula

```text
Clean anime-fantasy shell
+ contextual character artwork
+ elemental accent
+ restrained glass
+ thin fantasy ornament
+ strong information hierarchy
+ progressive disclosure
= Project G visual identity
```

---

# 45. Design Review Checklist

Trước khi chấp nhận một màn hình, kiểm tra:

- Có biết ngay hành động chính không?
- Có đúng một visual anchor không?
- Artwork có hỗ trợ hierarchy thay vì phá hierarchy không?
- Có quá nhiều panel/card ngang cấp không?
- Ornament có vượt qua nội dung không?
- Elemental color có bị dùng quá mức không?
- State có đọc được khi bỏ màu không?
- Các chi tiết kỹ thuật có thể ẩn sâu hơn không?
- CTA chính có nổi bật rõ ràng không?
- Người mới có thể hiểu màn hình mà không đọc tài liệu không?
- Layout có còn rõ khi scale xuống màn hình nhỏ hơn không?
- Motion có mục đích không?

---

# 46. Final Principle

Project G nên học từ cách Genshin giữ một **global visual grammar ổn định** nhưng cho phép từng nhân vật, nguyên tố và vùng có identity riêng.

Không cố làm mọi màn hình “đẹp” bằng cách tăng chi tiết.

Thay vào đó:

**giữ structure ổn định, cho nội dung game tạo cá tính, và để visual hierarchy quyết định mọi thứ.**
