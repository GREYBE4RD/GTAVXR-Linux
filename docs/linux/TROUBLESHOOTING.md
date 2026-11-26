# Troubleshooting

## Inspect a launch

The launcher prints the active session directory, normally below `~/.local/share/gtavxr-linux/sessions/`.

For example, to find eye-chain logs for the latest session:

```bash
find "$HOME/.local/share/gtavxr-linux/sessions" -type f -name xr.log -print | sort | tail -n 3
```

A line such as `EYE_CHAIN state=blit_fallback stage=sr_init code=0xBAD00002` means the requested upscaler failed to initialize. A later `EYE_CHAIN eye=0 path=bilinear` and eye=1 indicates the fallback is active for both eyes. A successful bridge state alone does not confirm OptiScaler used FSR rather than DLSS: check OptiScaler's actual backend and both headset images.

OptiScaler v0.9.5 loaded with Linux v1.6 but the official NVIDIA model returned `sr_init=0xBAD00002` on RX 9070 XT. Linux v1.7 instead tests a separate NGX forwarder and keeps the original runtime intact. The new route requires live verification.

## SteamVR compositor workaround

**Warning:** The Linux launcher can modify SteamVR's installed `vrcompositor` binary for all VR applications. The patch remains installed after GTAVXR exits. It is unofficial, version-specific and may be overwritten by SteamVR updates.

SteamVR 2.19.3 has a reported Vulkan descriptor-pool failure with `vulkanrenderer.cpp:3719` ([ValveSoftware/SteamVR-for-Linux #1067](https://github.com/ValveSoftware/SteamVR-for-Linux/issues/1067)). The GTAVXR test environment reproduced a compositor failure. An experimental descriptor-pool workaround has been tested on specific SteamVR 2.19.3 and 2.19.5 binaries.

The launcher only patches when the complete original SHA-256 matches a known build. It verifies the exact original instruction bytes, verifies the result against a pinned patched SHA-256, and retains a verified copy of the original executable. All unknown or updated builds are left unchanged.

| SteamVR build | Original max descriptor sets | Patched sets | Backup |
| --- | ---: | ---: | --- |
| 2.19.3 (verified binary) | 200 | 10,000 | `~/.local/share/steamvr-backups/vrcompositor-v1.0` |
| 2.19.5 (verified binary) | 512 | 10,000 | `~/.local/share/steamvr-backups/vrcompositor-v2.0` |

When it finds a supported but unpatched compositor, the launcher requires SteamVR to be stopped and asks for explicit confirmation before modifying it. A previously patched compositor does not trigger another prompt. Manual commands:

```bash
python3 gtavxr-linux.py steamvr-status
python3 gtavxr-linux.py steamvr-patch
python3 gtavxr-linux.py steamvr-restore
```

The restore command verifies the exact patched executable and matching original backup before replacing it. Close SteamVR before restoring. Uninstalling GTAVXR does **not** restore SteamVR automatically. If SteamVR has updated, the launcher refuses to restore an old executable over the new build.

## Known VR rendering and performance limitations

The SteamVR patch restores initial rendering in some setups but **does not guarantee continuous VR operation** or full refresh-rate rendering. One tested setup with an RX 9070 XT and Steam Frame still drops to 36 FPS at 72 Hz and can lose the headset image while the game continues on the monitor. The cause has not been confirmed.

A separate user report in [GTAVXR issue #105](https://github.com/LVL-VR/GTAVXR/issues/105) describes a possible wrist HUD OpenXR quad-layer issue and a workaround using `wrist_hud=0` in `~/.local/share/gtavxr-linux/vr-settings.ini`. **That explanation and workaround have not yet been tested or confirmed on the Steam Frame setup.** Disabling the wrist HUD may also remove HUD elements and subtitles from the headset. The launcher does not change this setting automatically.
