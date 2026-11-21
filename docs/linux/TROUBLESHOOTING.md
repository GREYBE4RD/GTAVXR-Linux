# Troubleshooting

## Inspect a launch

The launcher prints the active session directory, normally below `~/.local/share/gtavxr-linux/sessions/`.

For example, to find eye-chain logs for the latest session:

```bash
find "$HOME/.local/share/gtavxr-linux/sessions" -type f -name xr.log -print | sort | tail -n 3
```

A line such as `EYE_CHAIN state=blit_fallback stage=sr_init code=0xBAD00002` means the requested upscaler failed to initialize. A later `EYE_CHAIN eye=0 path=bilinear` and eye=1 indicates the fallback is active for both eyes. A successful bridge state alone does not confirm OptiScaler used FSR rather than DLSS: check OptiScaler's actual backend and both headset images.

OptiScaler v0.9.5 loaded with Linux v1.6 but the official NVIDIA model returned `sr_init=0xBAD00002` on RX 9070 XT. Linux v1.7 instead tests a separate NGX forwarder and keeps the original runtime intact. The new route requires live verification.

### SteamVR compositor workaround

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

