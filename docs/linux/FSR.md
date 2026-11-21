# Experimental FSR / DLSS bridge

**Status: unverified.** This is an experimental alternate *NGX forwarder* that redirects GTAVXR's existing per-eye DirectX 12 Super Resolution calls to the user's own OptiScaler. It does not implement AMD's FidelityFX SDK itself. Actual FSR 3/4 activation and correct VR stereo rendering have **not** been established.

The ordinary launch and official runtime **remain unchanged**, including NVIDIA DLSS and Neural Rendering. Disable FSR simply by running the launcher without `--fsr`. Do not enable FSR frame generation in VR.

## Build the alternate forwarder

The alternate binary `nvngx.dll_gtavxr_sr.dll` is **not** part of the official GTAVXR release. Download it from this repository's [GitHub Actions build artifact](https://github.com/GREYBE4RD/GTAVXR-Linux/actions/workflows/fsr-forwarder.yml) when a successful `gtavxr-fsr-forwarder-v1.7` build is available, then extract the DLL. Alternatively, compile it on Windows x64 with the commands in [code/bridge/fsr-forwarder/README.md](../../code/bridge/fsr-forwarder/README.md).

The original `nvngx.dll_gtavxr_sr.dll` from the GTAVXR 1.0.5 runtime is **not** the FSR build and is refused if supplied as the alternate forwarder.

## Required files

- Official [OptiScaler v0.9.5](https://github.com/optiscaler/OptiScaler/releases/tag/v0.9.5) extracted locally, including `OptiScaler.dll`, `OptiScaler.ini` and optional backend libraries.
- A separately supplied 64-bit `nvngx_dlss.dll` from a legitimately installed game or NVIDIA package. It is not distributed here.
- The experimental FSR forwarder built from this repository.

The launcher uses the original NVIDIA model only as an input to OptiScaler and for GTAVXR's existing model-file check. In FSR mode, the alternate forwarder loads OptiScaler rather than initializing that NVIDIA DLL directly. Whether OptiScaler can process these calls correctly remains to be tested.

## Test FSR 3 first

With SteamVR running, use the actual location of your built forwarder:

```bash
python3 "$HOME/Downloads/gtavxr-linux.py" launch --fsr 3 --optiscaler-dir "$HOME/Downloads/OptiScaler-v0.9.5" --fsr-dlss-dir "/mnt/linflux2/SteamLibrary/steamapps/common/Cyberpunk 2077/bin/x64" --fsr-forwarder "/path/to/nvngx.dll_gtavxr_sr.dll" --dry-run
```

Remove `--dry-run` only after the inputs validate. The launcher copies OptiScaler and a verified upstream bridge into an isolated session directory; the original game and upstream runtime are not changed. OptiScaler's custom configuration selects the FSR 3.1 DirectX 12 backend and turns frame generation off.

FSR 4 can be requested by changing `--fsr 3` to `--fsr 4`. This also requests `PROTON_FSR4_UPGRADE=1`, but **it does not install the AMD FSR 4 DLL**. The required AMD runtime components may be missing from standard Proton builds. FSR 4 must not be claimed active unless the backend log confirms it.

## Verification

Inspect the latest `sessions/<id>/native/activation-*/xr.log` files. The initial test must have an `EYE_CHAIN state=chain ... sr=1` line, followed by an `EYE_CHAIN pair ... left_sr=1 ... right_sr=1` line. Also check OptiScaler's log for its actual selected upscaler, and inspect both eyes for ghosting, mismatched projection and flicker. Even a successful NGX bridge does not prove the output uses FSR.

If the bridge logs `state=blit_fallback`, it used bilinear upscaling rather than FSR. For known problems see [Troubleshooting](TROUBLESHOOTING.md).

**No FSR support is claimed for public releases until these tests pass.**
