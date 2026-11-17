# GTAVXR Linux

Linux installer and launcher for [GTAVXR by LVL](https://github.com/LVL-VR/GTAVXR), using **GTA V Legacy** and **Proton** with **SteamVR/OpenXR**. This repository is a Linux-focused fork. The original GTAVXR 1.0.2 source, documentation, and third-party notices are retained in `code/`, `docs/`, and `THIRD_PARTY_NOTICES.md`.

**Status:** experimental Linux launcher v1.3. Tested on Arch Linux with an AMD RX 9070 XT, Proton 11.0, SteamVR 2.19.3 and Steam Frame. Other GPUs, headsets, distributions and Proton versions have not been verified. This is not a native Linux port; the launcher runs the Windows GTAVXR game through Proton.

## Requirements

- A legitimate Steam installation of **GTA V Legacy build 1.0.3889.0**. GTA V Enhanced and other Legacy builds are not supported by this release. The launcher verifies the retail `GTA5.exe` hash before installing.
- Steam, a working Proton installation, and SteamVR configured as the active OpenXR runtime. Connect the headset and start SteamVR before playing.
- Python 3, the system `libzstd` library, and [rage-cli](https://github.com/VIRUXE/rage-cli/releases) (the executable is named `rage`; v0.28.1 was used for testing). Put `rage` at `~/.local/bin/rage`, or pass `--rage /path/to/rage`.
- The extracted, official **GTAVXR 1.0.2 payload ZIP** saved as `~/Downloads/GTAVXR-payload.zip`, or provided using `--payload /path/to/GTAVXR-payload.zip`. The official Windows [GTAVXR.exe release](https://github.com/LVL-VR/GTAVXR/releases) contains the embedded release assets. **The Windows EXE is not directly accepted as the payload ZIP**, and extraction is not automated in v1.3. This is currently a manual prerequisite for a fresh installation.

The repository does **not** include GTA V game files, the proprietary GTAVXR release payload, or patched SteamVR executables.

On Arch Linux, install the common system dependencies with `sudo pacman -S python zstd`. Install `rage` separately using the upstream Linux release. Proton, SteamVR, and the Steam client must already work on your machine.

## Run

Download [gtavxr-linux-v1.3.py](gtavxr-linux-v1.3.py), open a terminal in the directory containing it, and run:

```bash
python3 gtavxr-linux-v1.3.py
```

No command argument is needed. The script detects registered Steam libraries, GTA V Legacy, Proton, and SteamVR. If GTAVXR is missing, it prompts to install; once installed, it checks the installation and launches the game. On first launch, it offers to copy existing Story Mode saves into an **isolated VR Proton prefix**, preserving normal GTA saves. On later launches it preserves the VR saves and settings.

The first installation reconstructs and SHA-256 verifies GTAVXR assets using the official payload and your own retail GTA files. This can take some time and needs temporary disk space.

For diagnostics, the existing commands remain available:

```bash
python3 gtavxr-linux-v1.3.py status
python3 gtavxr-linux-v1.3.py verify
python3 gtavxr-linux-v1.3.py repair
python3 gtavxr-linux-v1.3.py launch --dry-run
python3 gtavxr-linux-v1.3.py import-saves
python3 gtavxr-linux-v1.3.py uninstall
```

Use `--game`, `--proton`, `--steam`, or `--payload` when automatic detection does not find the correct path. Use `--help` for all options.

## SteamVR compositor workaround

SteamVR 2.19.3 has a reported Vulkan descriptor-pool failure, which can crash `vrcompositor` with `vulkanrenderer.cpp:3719` ([ValveSoftware/SteamVR-for-Linux issue #1067](https://github.com/ValveSoftware/SteamVR-for-Linux/issues/1067)). This was reproduced with Steam Frame and RADV; the GTAVXR test setup also exhibited this crash.

On each normal launch, the script checks the SteamVR compositor binary. It automatically applies the community workaround **only** if the original compositor matches the known SHA-256. It verifies the patch before writing, preserves a backup, and prints whether the fix was applied, already present, or skipped. The change enlarges a Vulkan descriptor pool from 200 to 10,000 sets.

**SteamVR must be fully stopped before the initial patch is applied.** If you start the launcher with the unpatched compositor while SteamVR is running, it will ask you to close SteamVR and retry. After patching, start SteamVR and run the launcher again to play. A patched binary is left installed when GTA exits, including for other VR games. This is an **unofficial, version-specific binary patch**; it is not guaranteed safe for future SteamVR updates. Unsupported compositor hashes are not modified.

Maintenance commands:

```bash
python3 gtavxr-linux-v1.3.py steamvr-status
python3 gtavxr-linux-v1.3.py steamvr-patch
python3 gtavxr-linux-v1.3.py steamvr-restore
```

The original compositor is backed up at `~/.local/share/steamvr-backups/vrcompositor-v1.0`. Close SteamVR before restoring. SteamVR updates may overwrite the fix. Do not apply the old patch to an updated binary.

## Saves, settings, and removal

- **VR-only Proton prefix:** `~/.local/share/gtavxr-linux/compatdata/271590`. Original GTA V's Steam Proton prefix is not shared.
- **VR settings and sessions:** `~/.local/share/gtavxr-linux/`. Session logs are retained for troubleshooting.
- **Graphics settings:** The launcher enforces supported `settings.xml` values on actual launches. In particular, `ShaderQuality` must be at least 1; a value of 0 can cause `common:/shaders/im` startup failure.
- **Story saves:** Regular GTA Story Mode saves can be copied into VR. Existing VR save slots are not overwritten during import.
- **Optional GTA V mods:** Not installed by the Linux launcher. In-game GTAVXR settings, including soft engine rumble under **VR Menu → Settings → Haptics**, remain user-controlled.
- **Uninstall:** `uninstall` removes only verified launcher-owned game files. It does not erase the VR save prefix, session logs, original GTA saves, or the SteamVR backup or patch.

## Upstream and credits

GTAVXR is developed by [LVL-VR](https://github.com/LVL-VR/GTAVXR). This fork adds a separate Linux installer/launcher without claiming ownership of upstream GTAVXR code or assets. Keep upstream copyright, license, and attribution requirements when redistributing or updating source components.

- [Original GTAVXR project](https://github.com/LVL-VR/GTAVXR)
- [Upstream VR controls](docs/VR_CONTROLS.md)
- [Upstream in-game menu](docs/VR_MENU.md)
- [Upstream Story Mode saves](docs/SAVES.md)
- [Upstream third-party notices](THIRD_PARTY_NOTICES.md)
- [Linux launcher changelog](CHANGELOG.md)
