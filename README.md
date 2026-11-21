# GTAVXR Linux

Linux installer and launcher for [GTAVXR](https://github.com/LVL-VR/GTAVXR) on **GTA V Legacy**, using Proton, SteamVR and OpenXR.

**Version:** Linux v1.7, supporting upstream GTAVXR 1.0.5. Experimental, tested mainly with Arch Linux, RX 9070 XT and Steam Frame. This is not a native Linux port.

## Requirements

- Legitimate GTA V Legacy **1.0.3889.0** (not Enhanced).
- Working Steam, Proton and SteamVR (OpenXR runtime).
- Python 3, `libzstd` and [rage-cli](https://github.com/VIRUXE/rage-cli/releases).

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
