# GTAVXR Linux

Linux installer and launcher for [GTAVXR by LVL](https://github.com/LVL-VR/GTAVXR), using **GTA V Legacy** and **Proton** with **SteamVR/OpenXR**. This repository is a Linux-focused fork. The upstream source snapshot, documentation, and third-party notices are retained in `code/`, `docs/`, and `THIRD_PARTY_NOTICES.md`.

**Status:** experimental Linux launcher v1.6 (GTAVXR upstream 1.0.5). Tested on Arch Linux with an AMD RX 9070 XT, Proton 11.0, SteamVR 2.19.3 and Steam Frame. Other GPUs, headsets, distributions and Proton versions have not been verified. This is not a native Linux port; the launcher runs the Windows GTAVXR game through Proton.

## Requirements

- A legitimate Steam installation of **GTA V Legacy build 1.0.3889.0**. GTA V Enhanced and other Legacy builds are not supported by this release. The launcher verifies the retail `GTA5.exe` hash before installing.
- Steam, a working Proton installation, and SteamVR configured as the active OpenXR runtime. Connect the headset and start SteamVR before playing.
- Python 3, the system `libzstd` library, and [rage-cli](https://github.com/VIRUXE/rage-cli/releases) (the executable is named `rage`; v0.28.1 was used for testing). Put `rage` at `~/.local/bin/rage`, or pass `--rage /path/to/rage`.
- Network access for the initial installation (unless you already have a local payload ZIP or the exact official `GTAVXR.exe`). The launcher downloads the pinned [upstream GTAVXR 1.0.5 release](https://github.com/LVL-VR/GTAVXR/releases/tag/v1.0.5) and extracts its embedded assets automatically. No Windows installer execution or manual extraction is required. The original EXE is verified against the upstream SHA-256 `83469b72c10f2d35f9f6025c4e31c75ae7632e413165b46343749de5a31fff7c`.

The repository does **not** include GTA V game files, the proprietary GTAVXR release payload, or patched SteamVR executables. The retained upstream source snapshot may lag behind the GTAVXR version downloaded by the Linux launcher.

On Arch Linux, install the common system dependencies with `sudo pacman -S python zstd`. Install `rage` separately using the upstream Linux release. Proton, SteamVR, and the Steam client must already work on your machine.

This command will download the precompiled `rage` binary, verifies its SHA-256 checksum, and makes it executable. No compilation or sudo is required. e.g.
```bash
mkdir -p ~/.local/bin && curl -fL https://github.com/VIRUXE/rage-cli/releases/download/v0.28.1/rage-linux-x86_64 -o ~/.local/bin/rage && echo "dd0134c89b74302d489ccd5e2e57b172425fa12ba14572016fad7e8e10e3c109  $HOME/.local/bin/rage" | sha256sum -c - && chmod +x ~/.local/bin/rage && ~/.local/bin/rage --version
```

## Run

For a first installation or to download an updated Linux launcher, run this one-line command in a terminal:

```bash
mkdir -p "$HOME/Downloads" && curl -fL https://raw.githubusercontent.com/GREYBE4RD/GTAVXR-Linux/main/gtavxr-linux.py -o "$HOME/Downloads/gtavxr-linux.py" && chmod +x "$HOME/Downloads/gtavxr-linux.py" && "$HOME/Downloads/gtavxr-linux.py"
```

This creates `~/Downloads` if necessary, downloads the current `gtavxr-linux.py` from the repository's `main` branch (replacing an older downloaded copy), makes it executable, and runs it. The launcher finds GTA V Legacy, Proton, and SteamVR, then offers to install GTAVXR or update a supported older installation. Once installation checks pass, it launches the game.

**To run GTAVXR normally on later sessions**, start SteamVR, connect your headset, and run the existing launcher without downloading it again:

```bash
"$HOME/Downloads/gtavxr-linux.py"
```

To get a newer Linux launcher in the future, repeat the first one-line download command. The executable permission will be applied again. Running the script with `python3 "$HOME/Downloads/gtavxr-linux.py"` also works and does not require executable permission.

System prerequisites listed above must already be installed. Because these commands run downloaded code, review the [launcher source](gtavxr-linux.py) before use if desired.

Alternatively, [download gtavxr-linux.py](gtavxr-linux.py) manually, open a terminal in the directory containing it, and run:

```bash
python3 gtavxr-linux.py
```

No command argument is needed. The script detects registered Steam libraries, GTA V Legacy, Proton, and SteamVR. If GTAVXR is missing, it prompts to install; once installed, it checks the installation and launches the game. On first launch, it offers to copy existing Story Mode saves into an **isolated VR Proton prefix**, preserving normal GTA saves. On later launches it preserves the VR saves and settings.

On first installation, if no local `~/Downloads/GTAVXR-payload-v1.0.5.zip` exists, the script downloads the official 1.0.5 `GTAVXR.exe`, verifies its published SHA-256, locates and checks the embedded payload ZIP, and reconstructs GTAVXR using your own GTA V retail files. Temporary download and extraction files are deleted after installation or on error. The installer itself is never executed. This process can take time and needs temporary disk space.

For offline installations, use `--installer /path/to/GTAVXR.exe` with an already downloaded **official 1.0.5** installer, or `--payload /path/to/GTAVXR-payload-v1.0.5.zip` with a previously extracted ZIP. These sources are read locally. Use `--no-download` to prevent any automatic network download. When GTAVXR is already installed and verified, starting it does not download anything.

For diagnostics, the existing commands remain available:

```bash
python3 gtavxr-linux.py status
python3 gtavxr-linux.py verify
python3 gtavxr-linux.py repair
python3 gtavxr-linux.py update
python3 gtavxr-linux.py launch --dry-run
python3 gtavxr-linux.py import-saves
python3 gtavxr-linux.py uninstall
```

Use `--game`, `--proton`, `--steam`, `--installer`, or `--payload` to select explicit locations. Use `--help` for all options.

## Updating from GTAVXR 1.0.2

The Linux v1.5 launcher recognises the verified GTAVXR 1.0.2 installation created by the earlier Linux launcher. Run `python3 gtavxr-linux.py` as usual. If the old version is detected, it offers to update to **GTAVXR 1.0.5** before launching. You can also use `python3 gtavxr-linux.py update` directly.

The upgrade verifies the old installation and reconstructs the new version before replacing any files. It backs up its existing managed files, installs the new release, and verifies the result. On failure it restores the old installation. If the process is interrupted during replacement, the next normal run recovers the previous installation from the saved upgrade journal. **Do not manually delete the upgrade journal or backup directory.**

The isolated VR Proton prefix, existing Story Mode saves, imported saves, and `~/.local/share/gtavxr-linux/vr-settings.ini` are preserved. No additional GTA V mods are installed. If the 1.0.2 installation has missing or modified files, repair it first with the previous Linux v1.4 launcher. The new installer will not overwrite unrecognised files.

**Testing status:** Version 1.5 has passed Python syntax, synthetic embedded-bundle validation, upgrade, rollback and interruption-recovery tests. The full 1.0.5 download, reconstruction and gameplay have not yet been tested on a live GTA V installation. Back up your saves independently before performing a first live upgrade.

## Experimental FSR test (Linux v1.6)

**Opt-in and unverified for GTAVXR.** GTAVXR uses custom DLSS forwarders and independent per-eye rendering. OptiScaler's standard injection may not intercept these calls, or may produce incorrect stereo images. **Do not consider FSR active merely because the launcher prints "FSR test requested."** Confirm the active upscaler in OptiScaler's logs and verify *both* headset views before claiming a performance benefit.

This experiment uses [OptiScaler](https://github.com/optiscaler/OptiScaler) v0.9.5. It is **not bundled or downloaded** by the launcher. Obtain the [official release](https://github.com/optiscaler/OptiScaler/releases/tag/v0.9.5), extract its `.7z` archive and find the directory containing `OptiScaler.dll` and `OptiScaler.ini`. You must also supply a legitimate 64-bit `nvngx_dlss.dll` file in a separate local directory, or alongside OptiScaler. GTAVXR's existing DLSS SR path requires the file. Neither package is redistributed here.

Run with both local directories adjusted to your files (example for FSR 4 on an RDNA 4 GPU):

```bash
python3 gtavxr-linux.py launch --fsr 4 --optiscaler-dir "/path/to/extracted/OptiScaler" --fsr-dlss-dir "/path/to/dlss"
```

For FSR 3, change `--fsr 4` to `--fsr 3`. Add `--dry-run` for preflight checks without staging game files. To return to the normal launch, omit the FSR options.

The launcher temporarily stages the OptiScaler loader as `winmm.dll`, a separate `OptiScaler.ini`, and any matching support DLLs/resource folders from the extracted package. It refuses filenames already present in the GTA directory. It sets Wine's `winmm=n,b` override, requests FSR 3.1 as the backend (and requests an FSR 4 upgrade with `--fsr 4`), and selects SR Quality in a **temporary per-session VR settings file**. Your usual VR settings remain unchanged. Frame generation is disabled. The verified SteamVR compositor patch and existing AMD workaround are unchanged.

The staged game files are removed when GTA exits. If a session is interrupted, the next normal launch uses a recorded file journal to recover them after GTA closes. It refuses to delete modified files. Logs generated independently by OptiScaler are not managed by this cleanup.

**Testing status:** Python syntax and simulated file staging, configuration, cleanup, crash recovery and collision tests passed. Actual FSR activation, DLL interception, stereoscopic rendering, and gameplay under Proton have **not** been verified. If GTAVXR bypasses the usual OptiScaler hooks, a GTAVXR-specific bridge change will be required.

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
