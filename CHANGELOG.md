# GTAVXR changelog
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
