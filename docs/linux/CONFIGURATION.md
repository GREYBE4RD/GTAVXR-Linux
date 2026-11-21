# Configuration, saves and graphics

## Saves, settings, and removal

- **VR-only Proton prefix:** `~/.local/share/gtavxr-linux/compatdata/271590`. Original GTA V's Steam Proton prefix is not shared.
- **VR settings and sessions:** `~/.local/share/gtavxr-linux/`. Session logs are retained for troubleshooting.
- **Graphics settings:** The launcher enforces supported `settings.xml` values on actual launches. In particular, `ShaderQuality` must be at least 1; a value of 0 can cause `common:/shaders/im` startup failure.
- **Story saves:** Regular GTA Story Mode saves can be copied into VR. Existing VR save slots are not overwritten during import.
- **Optional GTA V mods:** Not installed by the Linux launcher. In-game GTAVXR settings, including soft engine rumble under **VR Menu → Settings → Haptics**, remain user-controlled.
- **Uninstall:** `uninstall` removes only verified launcher-owned game files. It does not erase the VR save prefix, session logs, original GTA saves, or the SteamVR backup or patch.

## Graphics choices

The **normal** launch uses the upstream GTAVXR implementation and original NGX/DLSS forwarders. Use GTAVXR's own settings to enable or disable DLSS on a compatible NVIDIA GPU. On AMD, run without an FSR option for the known native/bilinear path.

The optional `--fsr 3` or `--fsr 4` experiment creates a per-session copy of the VR graphics profile with `[Graphics] upscale=quality, neural=0`. It does not alter the user's saved `~/.local/share/gtavxr-linux/vr-settings.ini`. Frame generation is disabled for VR tests. [FSR instructions](FSR.md).

The AMD workaround `dxgi.customVendorId = 8086` is still applied by default because the installed GTAVXR 1.0.5 executable has a known AMD-related loading issue. Disabling it with `--no-amd-workaround` can prevent GTAVXR from launching.
