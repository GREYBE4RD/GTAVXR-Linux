# GTAVXR Linux v1.8: opt-in OpenXR frame timing

This diagnostic patch is based on GTAVXR-Linux v1.7. It does **not** change
frame pacing, settings, the installed GTAVXR runtime, or game saves.

## Build the diagnostic DLL

Apply `GTAVXR-Linux-v1.8.patch` at the root of your GTAVXR-Linux checkout:

```sh
git apply --check /path/to/GTAVXR-Linux-v1.8.patch && git apply /path/to/GTAVXR-Linux-v1.8.patch
```

Commit and push this branch, then use GitHub Actions > "Build GTAVXR CPU timing
diagnostic bridge" > "Run workflow". Download the
`gtavxr-xr-timing-v1.8` artifact and extract `gtavxr_native_openxr.dll`.
This workflow requires a GitHub Actions Windows runner, Windows SDK, CMake,
and access to the upstream OpenXR SDK headers. The patch does not include a
prebuilt DLL.

## Launch with Proton 11.0

From the patched checkout, with SteamVR running and Steam Frame connected:

```sh
python3 gtavxr-linux.py launch --timing-bridge "$HOME/Downloads/gtavxr_native_openxr.dll" 2>&1 | tee >(wl-copy)
```

The installed runtime remains unchanged: the launcher verifies its existing
files, then passes the explicit diagnostic DLL path only to this session.
The `--timing-bridge` option also sets `GTAVXR_TIMING180=1` in the Proton
environment. Do **not** combine it with `--fsr`.

Test the same indoor and outdoor locations at 72 Hz. Aim for at least 120
frames in each location. Locate the session's `xr.log` with:

```sh
find "$HOME/.local/share/gtavxr-linux/sessions" -type f -name 'xr.log' -print 2>&1 | tee >(wl-copy)
```

Look for `XR_TIMING180` entries. Each entry summarises 120 frames:

- `wait_*` is elapsed time inside `xrWaitFrame`.
- `begin_*` is elapsed time inside `xrBeginFrame`.
- `locate_*` is elapsed time inside `xrLocateViews`.
- `bridge_begin_other_*` is remaining time inside the bridge begin operation.
- `between_calls_*` is elapsed time after the bridge begin operation and before
  bridge finish; it includes GTA rendering, other game work and **any waits**.
- `bridge_finish_prep_*` is time preparing layers before `xrEndFrame`.
- `end_*` is elapsed time inside `xrEndFrame`.
- `cadence_*` is elapsed time between calls to the bridge begin operation.
- `period_avg_ms` is the OpenXR `predictedDisplayPeriod` reported by SteamVR;
  `should_not_render` counts frames where `shouldRender` was false.

These are **wall-clock** measurements on the rendering thread, not CPU
utilisation or GPU execution times. A slow `xrEndFrame` or `xrWaitFrame` shows
where blocking occurs but cannot by itself prove whether SteamVR or the game
caused it. Low GPU utilisation also does not rule out a CPU bottleneck.

## Disable

Launch GTAVXR without `--timing-bridge` using your normal v1.7 command.
The `GTAVXR_TIMING180` mode is off by default. The older GPU-based PERF147
profiling mode remains disabled in all cases.
