# GTAVXR Linux v1.10: cross-thread capture timing

The v1.9 timing recorder measured only calls made on the frame-begin thread.
In the previous test it reported zero world-eye capture calls, so it may have
missed captures performed by another thread. This version independently
records these operations without requiring the caller to be the begin thread.

The new recorder runs only for an opted-in diagnostic bridge with
`GTAVXR_TIMING1100=1`. The launcher supplies this when `--timing-bridge` is
selected. The normal installed bridge is not replaced. No additional GPU
query, D3D11 Flush, swapchain wait or rendering operation is introduced.

## Build and launch

Manually run the GitHub Actions workflow **Build GTAVXR v1.10 timing diagnostic
bridge** on the branch containing this patch. Download its artifact
`gtavxr-xr-timing-v1.10`, extract `gtavxr_native_openxr.dll` to
`~/Downloads` (replace the previous downloaded diagnostic DLL only), and run:

```sh
cd "$HOME/GTAVXR-Linux" && python3 gtavxr-linux.py launch --timing-bridge "$HOME/Downloads/gtavxr_native_openxr.dll" 2>&1 | tee >(wl-copy)
```

Use Proton 11.0 and SteamVR at 72 Hz. Test indoors at 72 FPS and outdoors
at 36 FPS, with at least 120 rendered frames in each location.

After closing the game, extract results:

```sh
log=$(find "$HOME/.local/share/gtavxr-linux/sessions" -type f -name 'xr.log' -printf '%T@ %p\n' | sort -nr | head -n 1 | cut -d' ' -f2-); { echo "Log: $log"; if [[ -n "$log" ]]; then grep -E 'XR_TIMING180|XR_TIMING190|XR_TIMING1100' "$log" | tail -n 100; else echo "No XR log found"; fi; } 2>&1 | tee >(wl-copy)
```

## What the new measurements mean

Every `XR_TIMING1100` log line summarises 120 *rendered* frames. Measurements
are CPU wall time per rendered frame (average and maximum), with call totals:

- `begin_tid_last`, `finish_tid_last`, `capture_tid_last`: thread IDs observed
  on the last frame in the window. `capture_tid_last=0` means no world-eye
  capture was observed on that final frame.
- `capture_on_begin_calls`, `capture_off_begin_calls`: number of world-eye
  captures performed by the frame-begin thread and other threads.
- `frames_no_capture`, `frames_off_thread_capture`,
  `finish_thread_mismatch_frames`: counts of frames with those conditions.
- `capture`: total wall time in exported world-eye capture calls, including
  waiting for the existing bridge lock. `capture_lock_wait` is the nested
  lock wait portion.
- `acquire`, `wait_image`, `copy_submit`, `flush`, `release`: CPU wall time
  inside world-eye capture. **These are already included in `capture`** and
  must not be added again. `copy_submit` is CPU submission, not GPU execution.
- `other_begin_thread`, `other_thread`: time in other exported bridge calls,
  separated by the frame-begin thread versus other threads. This includes
  lock acquisition time for those calls.

Different threads can execute concurrently outside the bridge. These elapsed
times can therefore overlap each other and the begin/finish frame interval.
Do not subtract off-thread time from `XR_TIMING180` `between_calls` or treat
its remainder as GTA V CPU execution. The older v1.9
`game_or_unmeasured` result may overstate time outside the bridge when
captures are performed by other threads.

The recorder reads and writes its frame counters only while the existing
exclusive bridge lock is held. Log-write failures disable this optional
recorder rather than faulting OpenXR. New timing calls use the existing
high-resolution clock but do not force GPU synchronisation.

## Return to normal

Run the launcher without `--timing-bridge` to use the unchanged installed
GTAVXR runtime.
