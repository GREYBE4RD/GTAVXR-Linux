# GTAVXR Linux

Linux installer and launcher for [GTAVXR](https://github.com/LVL-VR/GTAVXR) on **GTA V Legacy**, using Proton, SteamVR and OpenXR.

**Version:** Linux v1.13, supporting upstream GTAVXR 1.0.5. Experimental, tested mainly with Arch Linux, RX 9070 XT and Steam Frame. This is not a native Linux port.

## Requirements

- Legitimate GTA V Legacy **1.0.3889.0** (not Enhanced).
- Working Steam, Proton and SteamVR (OpenXR runtime).
- Python 3, `libzstd` and [rage-cli](https://github.com/VIRUXE/rage-cli/releases).

## Important: this launcher modifies SteamVR

**GTAVXR-Linux can patch the installed SteamVR `vrcompositor` executable.** Before it patches a supported, unmodified build for the first time, the launcher asks for explicit confirmation, including on a normal launch.

- **Supported builds:** specific, SHA-256 verified SteamVR 2.19.3 and 2.19.5 compositor binaries. Unknown builds are not modified.
- **Modification:** increases Vulkan descriptor-pool allocations and raises the maximum descriptor sets from 200 to 10,000 (2.19.3), or 512 to 10,000 (2.19.5).
- **Scope:** the modified executable is used by **all SteamVR applications**, not only GTAVXR. It stays modified after the game closes. A SteamVR update can overwrite the patch.
- **Backup and restore:** each supported version has a separate verified backup. SteamVR must be fully closed to patch or restore its executable.

Check with `python3 gtavxr-linux.py steamvr-status`. With SteamVR stopped, restore using `python3 gtavxr-linux.py steamvr-restore`.

**This is an unofficial experimental workaround.** It has restored initial GTAVXR rendering in testing, but it has not fixed the reported half-frame-rate problem or all OpenXR submission failures. Read [the SteamVR troubleshooting guide](docs/linux/TROUBLESHOOTING.md) before use.

## Install and play

Download and run the launcher:

```bash
mkdir -p "$HOME/Downloads" && curl -fL https://raw.githubusercontent.com/GREYBE4RD/GTAVXR-Linux/main/gtavxr-linux.py -o "$HOME/Downloads/gtavxr-linux.py" && python3 "$HOME/Downloads/gtavxr-linux.py"
```

It detects your Steam libraries, checks game files, offers to install/update GTAVXR and starts VR. Start SteamVR before playing. Initial installation can download the verified official Windows release; later launches work offline.

For later sessions:

```bash
python3 "$HOME/Downloads/gtavxr-linux.py"
```

Use `--help` for options. Run `status` to inspect your installation. GTA saves remain in an isolated VR Proton prefix.

## Optional FSR experiments

FSR 3/4 is **not yet verified in VR**. The Linux launcher can test an alternate forwarder that routes GTAVXR's existing per-eye upscaling calls to OptiScaler. Normal launches still use the **original, unchanged DLSS forwarder**. See [FSR setup and testing](docs/linux/FSR.md).

## Detailed guides

- [Installation and upgrades](docs/linux/INSTALLATION.md)
- [Configuration and saves](docs/linux/CONFIGURATION.md)
- [FSR and DLSS](docs/linux/FSR.md)
- [Troubleshooting and SteamVR fix](docs/linux/TROUBLESHOOTING.md)
- [Technical details and recovery](docs/linux/TECHNICAL.md)
- [Changelog](CHANGELOG.md)

## Credits

GTAVXR is developed by [LVL-VR](https://github.com/LVL-VR/GTAVXR). This repository maintains an experimental Linux launcher and bridge test. See [upstream third-party notices](THIRD_PARTY_NOTICES.md).

It was developed with assistance from OpenAI's ChatGPT; development and testing have used Arch Linux, SteamVR and Steam Frame.
