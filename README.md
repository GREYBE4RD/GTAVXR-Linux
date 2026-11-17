# GTAVXR Linux

Linux installer and launcher for [GTAVXR by LVL](https://github.com/LVL-VR/GTAVXR), using **GTA V Legacy** and **Proton** with **SteamVR/OpenXR**. This repository is a Linux-focused fork. The original GTAVXR 1.0.2 source, documentation, and third-party notices are retained in `code/`, `docs/`, and `THIRD_PARTY_NOTICES.md`.

**Status:** experimental Linux launcher v1.4. Tested on Arch Linux with an AMD RX 9070 XT, Proton 11.0, SteamVR 2.19.3 and Steam Frame. Other GPUs, headsets, distributions and Proton versions have not been verified. This is not a native Linux port; the launcher runs the Windows GTAVXR game through Proton.

## Requirements

- A legitimate Steam installation of **GTA V Legacy build 1.0.3889.0**. GTA V Enhanced and other Legacy builds are not supported by this release. The launcher verifies the retail `GTA5.exe` hash before installing.
- Steam, a working Proton installation, and SteamVR configured as the active OpenXR runtime. Connect the headset and start SteamVR before playing.
- Python 3, the system `libzstd` library, and [rage-cli](https://github.com/VIRUXE/rage-cli/releases) (the executable is named `rage`; v0.28.1 was used for testing). Put `rage` at `~/.local/bin/rage`, or pass `--rage /path/to/rage`.
- Network access for the initial installation (unless you already have a local payload ZIP or the exact official `GTAVXR.exe`). The launcher downloads the pinned [upstream GTAVXR 1.0.2 release](https://github.com/LVL-VR/GTAVXR/releases/tag/v1.0.2) and extracts its embedded assets automatically. No Windows installer execution or manual extraction is required. The original EXE is verified against the upstream SHA-256 `b6e996bbbb64f454227b33b04c7675d634324ae95dc702c973fcadd040afc013`.

The repository does **not** include GTA V game files, the proprietary GTAVXR release payload, or patched SteamVR executables.

On Arch Linux, install the common system dependencies with `sudo pacman -S python zstd`. Install `rage` separately using the upstream Linux release. Proton, SteamVR, and the Steam client must already work on your machine.

This command will download the precompiled `rage` binary, verifies its SHA-256 checksum, and makes it executable. No compilation or sudo is required. e.g.
```bash
mkdir -p ~/.local/bin && curl -fL https://github.com/VIRUXE/rage-cli/releases/download/v0.28.1/rage-linux-x86_64 -o ~/.local/bin/rage && echo "dd0134c89b74302d489ccd5e2e57b172425fa12ba14572016fad7e8e10e3c109  $HOME/.local/bin/rage" | sha256sum -c - && chmod +x ~/.local/bin/rage && ~/.local/bin/rage --version
```

## Run

Download [gtavxr-linux.py](gtavxr-linux.py), open a terminal in the directory containing it, and run:

```bash
python3 gtavxr-linux.py
```

No command argument is needed. The script detects registered Steam libraries, GTA V Legacy, Proton, and SteamVR. If GTAVXR is missing, it prompts to install; once installed, it checks the installation and launches the game. On first launch, it offers to copy existing Story Mode saves into an **isolated VR Proton prefix**, preserving normal GTA saves. On later launches it preserves the VR saves and settings.

On first installation, if no local `~/Downloads/GTAVXR-payload.zip` exists, the script downloads the official 1.0.2 `GTAVXR.exe`, verifies its published SHA-256, locates and checks the embedded payload ZIP, and reconstructs GTAVXR using your own GTA V retail files. Temporary download and extraction files are deleted after installation or on error. The installer itself is never executed. This process can take time and needs temporary disk space.

For offline installations, use `--installer /path/to/GTAVXR.exe` with an already downloaded **official 1.0.2** installer, or `--payload /path/to/GTAVXR-payload.zip` with a previously extracted ZIP. These sources are read locally. Use `--no-download` to prevent any automatic network download. When GTAVXR is already installed and verified, starting it does not download anything.

For diagnostics, the existing commands remain available:

```bash
python3 gtavxr-linux.py status
python3 gtavxr-linux.py verify
python3 gtavxr-linux.py repair
python3 gtavxr-linux.py launch --dry-run
python3 gtavxr-linux.py import-saves
python3 gtavxr-linux.py uninstall
```

Use `--game`, `--proton`, `--steam`, `--installer`, or `--payload` to select explicit locations. Use `--help` for all options.

## SteamVR compositor workaround

SteamVR 2.19.3 has a reported Vulkan descriptor-pool failure, which can crash `vrcompositor` with `vulkanrenderer.cpp:3719` ([ValveSoftware/SteamVR-for-Linux issue #1067](https://github.com/ValveSoftware/SteamVR-for-Linux/issues/1067)). This was reproduced with Steam Frame and RADV; the GTAVXR test setup also exhibited this crash.

On each normal launch, the script checks the SteamVR compositor binary. It automatically applies the community workaround **only** if the original compositor matches the known SHA-256. It verifies the patch before writing, preserves a backup, and prints whether the fix was applied, already present, or skipped. The change enlarges a Vulkan descriptor pool from 200 to 10,000 sets.

**SteamVR must be fully stopped before the initial patch is applied.** If you start the launcher with the unpatched compositor while SteamVR is running, it will ask you to close SteamVR and retry. After patching, start SteamVR and run the launcher again to play. A patched binary is left installed when GTA exits, including for other VR games. This is an **unofficial, version-specific binary patch**; it is not guaranteed safe for future SteamVR updates. Unsupported compositor hashes are not modified.

Maintenance commands:

```bash
python3 gtavxr-linux.py steamvr-status
python3 gtavxr-linux.py steamvr-patch
python3 gtavxr-linux.py steamvr-restore
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

It was developed with assistance from OpenAI's ChatGPT; development and testing have used Arch Linux, SteamVR and Steam Frame.
