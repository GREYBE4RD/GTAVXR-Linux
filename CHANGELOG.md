# GTAVXR changelog
## Linux launcher v1.9 (2026-11-22)

- Added opt-in v1.9 render-thread timing to the isolated diagnostic bridge, built separately through GitHub Actions.
- Reports world-eye capture, remaining bridge calls, swapchain acquire/wait/release, D3D11 submission and existing Flush wall time, plus remaining unmeasured time between begin and finish.
- Keeps v1.8's full frame timing output for direct comparison; ignores non-rendered frames in the new v1.9 samples.
- No default runtime changes, additional D3D11 Flush calls or GPU readback. Results measure elapsed CPU wall time, not GPU execution.

## Linux launcher v1.8 (2026-11-21)

- Added opt-in v1.8 OpenXR wall-time telemetry and a session-local diagnostic DLL option, without replacing the installed runtime.

## Linux launcher v1.7 (2026-11-21)

- Replaced the v1.6 generic `winmm.dll` injection test with an opt-in, session-local NGX bridge forwarder. The alternate DLL loads the user's own OptiScaler as the Super Resolution provider; it leaves the original DLSS forwarder and official GTAVXR runtime completely unchanged.
- Added Windows x64 source, CMake build and CI artifact for the alternate forwarder, plus offline Python isolation tests. A built forwarder must be supplied using `--fsr-forwarder`.
- The FSR path uses a separate VR profile, provider configuration and session runtime; it does not add or replace files in the GTA V directory. Normal launches still use the original verified DLLs.
- Shortened the main README and moved detailed setup, configuration, FSR, recovery and troubleshooting information to `docs/linux/`.
- **Not yet validated in real VR:** Native Windows compilation, FSR 3/4 provider initialization, GPU backend selection and correct stereo output still require GitHub Actions and headset tests. This remains a bridge-provider experiment, not a standalone AMD FidelityFX SDK backend.

## Linux launcher v1.6 (2026-11-21)

- Added an experimental opt-in `--fsr 3|4` OptiScaler test mode for GTAVXR 1.0.5 under Proton.
- Accepts user-supplied OptiScaler and DLSS input DLLs; configures Wine loading, FSR settings, and a temporary SR-enabled VR profile without changing normal VR settings.
- Disables VR frame generation; preserves the SteamVR workaround and existing DXVK AMD workaround.
- Temporarily stages additional files with a verified journal; refuses conflicts, removes unmodified files after game exit and recovers after interrupted sessions.
- Python syntax and simulated staging, cleanup and configuration tests passed. Real interception, FSR activation and stereo VR gameplay remain unverified.

## Linux launcher v1.5 (2026-11-18)

- Updated the pinned official GTAVXR installer to upstream 1.0.5 (new URL, size, SHA-256, executable hash and runtime-file inventory).
- Added automatic detection and upgrade of verified Linux GTAVXR 1.0.2 installations, with a default-Yes update prompt; added an explicit `update` command.
- Added SHA-256 verified backups and rollback for installer-managed game/runtime files. Interrupted updates are recovered on the next normal run.
- Preserved existing VR Proton prefix, Story Mode saves and VR settings. Refuses modified, incomplete or unowned files instead of overwriting them.
- Changed the default local ZIP name to `GTAVXR-payload-v1.0.5.zip` so the old 1.0.2 ZIP is not mistakenly reused. A verified official 1.0.5 Windows EXE is downloaded when needed.
- Kept the SteamVR workaround version-locked and unchanged; no additional mods.
- Syntax and simulated bundle/upgrade/rollback tests passed. Live 1.0.5 download, install and gameplay require user testing.

## Linux launcher v1.4 (2026-11-17)

- Automatically downloads the official GTAVXR 1.0.2 Windows release when no local payload ZIP is available.
- Checks the pinned release asset's size and SHA-256 before inspecting or extracting its embedded release ZIP.
- Extracts the embedded ZIP without running GTAVXR.exe or requiring an external Windows extraction utility; validates the payload identity and manifest.
- Uses temporary storage for the downloaded EXE and payload, removing both after installation, repair, or failure.
- Preserves local ZIP support and adds --installer for an official local EXE and --no-download for offline operation.
- Keeps existing v1.3 installation, save management, verified SteamVR patch and launch functionality unchanged.


## Linux launcher v1.3 (2026-11-17)

- Added an experimental Linux installer and launcher for GTA V Legacy 1.0.3889.0 through Proton and SteamVR.
- Added automatic Steam library and Proton detection, installation checks, first-install prompt, verification and repair.
- Added version-locked, SHA-256 verified SteamVR 2.19.3 descriptor-pool patch management with backup and restore.
- Added isolated VR Proton prefix, non-destructive Story Mode save import and supported graphics settings enforcement.
- No additional GTA V mods are installed. The original GTAVXR 1.0.2 source and release history remain upstream-owned.

## 1.0.2

- Added SteamVR support through OpenXR. Quest 3 via Steam Link verified in Story Mode. Fixed world presentation and duplicate SteamVR startup waits.
- Restored subtitles and objective text in VR and added movable subtitles with a placement guide. HUD changes keep notifications and wanted stars visible in more cases.
- Select the exact Story save before launching a profile. Start a new story or import saves into the existing profile.
- Migrate 1.0.0 profiles in place, choose where the Suite stores its data, and remove GTAVXR completely from managed locations.
- Expanded remapping for special ability, cover, stealth, phone, vehicle camera, aircraft fire and aircraft weapon selection. Added a choice of grip or trigger for weapon support and reload interaction with the free hand.
- Improved graphics and content compatibility checks, disk-space messages, and interrupted-session recovery.

## 1.0

First public release of GTAVXR by LVL.

- Install, configure, and launch GTAVXR from the Suite.
- Explore the open world and play Story Mode missions in VR with OpenXR, head tracking, and motion controllers.
- Manage saves by profile, copy your GTA V Legacy progress, or start a new story.
- Use the integrated Trainer and Script Host for compatible mods.
- Import content packs and choose graphics options by profile.
- Browse code and tests for individual components.

[Compatibility](docs/COMPATIBILITY.md) · [Known issues](docs/KNOWN_ISSUES.md)
