# Installation and upgrades

The launcher runs GTAVXR under Proton using the user's legitimate GTA V Legacy installation. It never runs the Windows release installer.

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

This creates `~/Downloads` if necessary, downloads the current `gtavxr-linux.py` from the repository's `main` branch (replacing an older downloaded copy), makes it executable, and runs it. The launcher finds GTA V Legacy, Proton, and SteamVR, then offers to install GTAVXR or update a supported older installation. A recognized, unpatched SteamVR compositor requires explicit confirmation before it is changed; read the warning on the main README. Once installation checks pass, it launches the game.

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

For normal use, the current Linux v1.13 launcher remains a single Python file named `gtavxr-linux.py`. Repeat the download command when the Python launcher changes. The launcher itself does not check GitHub for newer Python versions.
