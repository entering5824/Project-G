# Genshin Account Progression Planner

Native Windows desktop planner built with **Python + PySide6 + SQLite**.

The application runs entirely on the local machine. There is no React/Vite frontend, HTTP API, localhost server, cloud account, or paid API in the normal architecture.

All Python application code now lives under `src/projectg/`. The former `backend/app` Python package has been removed. See [`DESKTOP_ARCHITECTURE.md`](DESKTOP_ARCHITECTURE.md) for the enforced dependency rule.

## Run from source

From PowerShell at the repository root:

```powershell
py -m pip install -e ".[desktop]"
py -m projectg.main
```

Or run `setup.bat` once and then use `run.bat` / `start-planner.bat`. The repository virtual environment is `.venv/` at the project root.

The first native launch prepares the local data directory, migrates the SQLite database, and opens the PySide6 application. Live desktop state is stored under `%LOCALAPPDATA%\GenshinPlanner`.

For upgrades from an older checkout, the bootstrap still recognizes an optional historical `backend/data/` directory. If a legacy database exists there and no native database exists yet, it is copied once into `%LOCALAPPDATA%\GenshinPlanner`; the source is not mutated. `backend/` is no longer part of the current source tree.

Before changing an existing database schema, startup creates a `PRE_DESKTOP_MIGRATION` recovery archive in the local `backups` directory. If that archive cannot be created or validated, startup stops before applying the migration. Restore likewise creates a `PRE_RESTORE` archive before replacing local state.

## Build a Windows release

Double-click:

```text
build-desktop.bat
```

Output:

```text
dist\GenshinPlanner\GenshinPlanner.exe
dist\GenshinPlanner-portable.zip
```

The distribution bundles Qt, local GameData, the Build Knowledge Pack, Alembic configuration/migrations, and timezone data. Python is not required on the target machine after packaging.

## Architecture at a glance

```text
presentation -> interface_adapters -> application -> domain
infrastructure ---------------------> application ports -> domain
bootstrap -> concrete layers (composition root only)
```

Key rules are executable tests under `tests/architecture/`:

- `domain` is framework-independent and standard-library-only.
- `application` depends only on `domain` and application-owned ports/types.
- `application` cannot perform direct file/database/framework I/O.
- `interface_adapters` translate boundary representations without selecting drivers.
- `infrastructure` implements outbound ports and may depend inward.
- `presentation` does not reach into persistence.
- `bootstrap` is the only composition root that selects concrete implementations.
- the removed `app.*` namespace must not return to source, tests, packaging, or scripts.
- target validation/import-preview/preset-key policy lives in domain/application; SQLite only persists normalized target decisions.

## Product structure

The primary UI has four destinations:

- **Tiếp theo** — one concrete action to do now, with materials, blockers, and reasons.
- **Lộ trình** — stable account-wide strategic order and milestone chain.
- **Nhân vật** — observed account snapshot beside available build profiles.
- **Tier List** — score and control which characters join the automatic roadmap.

Import Account Snapshot JSON is the main input. The editor accepts the same v1 schema as manual entry; GOOD remains an import adapter. Legacy targets and manual artifact evaluations are retained in local history but do not control recommendations.

The planner reads the offline, versioned Build Knowledge Pack at `data/static/builds/build_profiles.json`. Verified Basic profiles for the full roster are sufficient for an account-wide baseline roadmap. Standard/Deep profiles improve archetype and artifact guidance as they are added; their coverage is reported separately and does not disable recommendations. Missing Basic profiles are reported rather than inferred from a generic character role.

The app does not store a material inventory. Planner farm quantities are calculated from progression targets and are theoretical estimates that do not subtract materials already owned. GOOD imports discard the optional `materials` section. Migration `0017_remove_inventory` removed the previous inventory tables and controls.

The legacy Target JSON contract remains available to inspect older account configuration exports. It is no longer part of the primary planner flow.

## Desktop keyboard navigation

- `Ctrl+1` to `Ctrl+4`: open Tiếp theo, Lộ trình, Nhân vật, or Tier List.
- `Ctrl+F`: focus and select the search text on the current searchable page.
- `Ctrl+R`: recalculate using the same action as the toolbar button.
- `Enter` in the roadmap table: read full details for the selected visible row.

The first-run view guides users through importing the account, ranking priorities,
and reviewing recommendations. Today keeps availability and resin cost beside the
recommended action; its roadmap button selects the matching goal when available.
Tier List shows ranking progress, invalid scores, and unsaved edits inline.

The desktop uses a left navigation rail on wide windows and a horizontal header
on compact windows. It has a shared page header and theme, visible keyboard focus, search-clear
buttons, a compact character action menu, and separate tier configuration actions.
Character cards reflow with window width. Artifact substats and Today supplementary
information can be expanded on demand. The Today
card fits the supported 800 × 560 minimum window without horizontal scrolling.

Roadmap and Tier List use compact columns by default. Enable **Chi tiết** to show
all columns; hidden values are still included when saving or exporting Tier List.
Use the main **Nhập tài khoản** button for Account Snapshot entry, or its arrow
menu to import a GOOD file. After import, the same action reads **Cập nhật tài khoản**.

## Local GameData packs

Runtime remains fully offline. The bundled dataset is generated from pinned `genshin-db@5.2.14` (Genshin 7.1). The desktop app can preview and install a newer local JSON pack from **Công cụ -> Dữ liệu -> GameData trên máy…**. The previous pack is backed up before replacement, and account coverage is shown before confirmation. Missing GameData is reported by Data Health; an unknown cost/source must never silently become zero.

For development/update work, build a pack from a pinned `genshin-db` npm package or source checkout:

```text
npm pack genshin-db@5.2.14
python scripts/build_gamedata_from_genshin_db.py genshin-db-5.2.14.tgz game_data.json --game-version 7.1 --data-version genshin-db-5.2.14
```

Validate the committed pack with:

```powershell
python scripts/validate_game_data.py
```

Validate Build Knowledge coverage with:

```powershell
python scripts/validate_build_profiles.py
```

## Teams

Use **Xuất kết quả…** in the desktop toolbar after loading an account to save a review ZIP. It contains `report.md` (readable recommendations, scores, reasons and resources), `results.json` (the complete latest loaded overview) and `review.md` (a feedback template). Export does not rerun the planner, change the account or apply screen search filters. Unzip the package and share it with reviewers; the result includes character and build data from the loaded account.

Planner ranks character/component goals. Mora, EXP, boss materials and other resource amounts are informational cost estimates (`requiredCost`); they never supply a priority score or block a goal. Only Talent Book domains affect Today availability. Today takes the first actionable semantic goal in Global order, skipping closed Talent goals; a pin restricts this selection to that character. Each Global row contains its complete `milestoneChain`. Shared farm sources do not merge goals or add a bonus.

Saved planner teams can designate exactly one **đội chính**. Membership in the primary team receives the stronger team-priority signal; appearing only in another saved team receives the smaller signal. Team configuration remains supplemental data and never changes the user's tier or target.


## Kiểm tra giao diện native

Giao diện sử dụng theme tối thống nhất và các nhóm **Công cụ → Lập kế hoạch / Dữ liệu / Hỗ trợ**.
Khi cập nhật lỗi, kết quả trước đó được giữ lại và có nút **Thử lại**. Form Snapshot và Settings cuộn được ở cửa sổ thấp.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
.venv\Scripts\python.exe scripts\verify_desktop_ui.py
```

Script dùng dữ liệu minh họa, không mở database tài khoản; ảnh được lưu ở `docs/ui-preview/v3`.
Chi tiết kiểm thử và giới hạn xác minh: [UI/UX audit](docs/UI_UX_AUDIT.md).
