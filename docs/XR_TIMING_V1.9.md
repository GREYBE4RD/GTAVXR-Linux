# GTAVXR Linux v1.9: isolate time between OpenXR frame calls

This optional diagnostic extends v1.8 without changing the installed GTAVXR
runtime, game saves, frame pacing, or normal launch behaviour. It uses existing
OpenXR operations and the existing D3D11 Flush. No extra GPU queries or waits.

## Build and launch

Apply `GTAVXR-Linux-v1.9.patch` to the *v1.8 main checkout* of GTAVXR-Linux,
commit and push, then manually run GitHub Actions > "Build GTAVXR v1.9 timing
diagnostic bridge". Download the `gtavxr-xr-timing-v1.9` artifact and extract
`gtavxr_native_openxr.dll` to `~/Downloads` (replace the previous v1.8
**downloaded diagnostic DLL** if it is still there). The game's installed DLL
must remain untouched.

Run with SteamVR/Steam Frame at 72 Hz and Proton 11.0:

```sh
cd "$HOME/GTAVXR-Linux" && python3 gtavxr-linux.py launch --timing-bridge "$HOME/Downloads/gtavxr_native_openxr.dll" 2>&1 | tee >(wl-copy)
```

The launcher sets `GTAVXR_TIMING180=1` and `GTAVXR_TIMING190=1` only for this
session. Do not combine `--timing-bridge` with `--fsr`. Test indoors and outdoors
for at least 120 **rendered** frames per area (about 3.3 seconds at 36 FPS).

Extract both log events from the latest session's `xr.log`:

```sh
log=$(find "$HOME/.local/share/gtavxr-linux/sessions" -type f -name 'xr.log' -printf '%T@ %p\n' | sort -nr | head -n 1 | cut -d' ' -f2-); { echo "Log: $log"; if [[ -n "$log" ]]; then grep -E 'XR_TIMING180|XR_TIMING190' "$log" | tail -n 70; fi; } 2>&1 | tee >(wl-copy)
```

## Interpret timing

`XR_TIMING190` reports **average and maximum milliseconds per rendered frame**
over 120 rendered frames, with `_calls` totals for that window:

- `world_capture`: full bridge call time for both world-eye captures, including
  waiting for the bridge lock.
- `other_bridge`: other bridge calls from the render thread during the interval.
- `game_or_unmeasured`: remainder after subtracting `world_capture` and
  `other_bridge` from the interval between the end of bridge begin and the start
  of bridge finish. Includes GTA engine work, any waits outside the bridge,
  unguarded bridge calls such as `compose`, and sampling overhead.
- `acquire`, `wait_image`, `copy_submit`, `flush`, `release`: CPU wall-clock
  time *inside* the world-eye capture functions. These measurements are nested
  within `world_capture` and **must not be added to it**. `copy_submit` measures
  CPU time to issue D3D11 commands, not GPU execution time. `flush` measures CPU
  time in the Flush call; no new Flush is performed.

Interpret these alongside `XR_TIMING180`'s `between_calls` and `period_avg_ms`.
A high `game_or_unmeasured` does **not** prove that GTA V is CPU-bound. An idle
CPU thread can be blocked on a GPU fence, DXVK, the driver, or the game engine.
To isolate those waits, profiling outside the bridge would be needed.

This timing code only runs when explicitly enabled, on the recorded render
thread, and it excludes `shouldRender=false` or otherwise non-visible frames.
Log failures disable the new recorder rather than faulting the OpenXR session.

## Return to normal

Launch without `--timing-bridge`. The normal v1.7 runtime installation remains
unchanged.
