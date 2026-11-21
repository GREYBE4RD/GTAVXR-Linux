# Technical details

The Linux launcher downloads only the pinned official GTAVXR 1.0.5 Windows release, checks its exact size and SHA-256, extracts a verified embedded ZIP and reconstructs game assets using `rage-cli` and `libzstd`. Its state file records owned files and hashes. The upgrade from 1.0.2 uses a journal and backup to recover safely after interruption. Do not delete the upgrade backup or journal manually.

**Original files are retained:** `gtavxr_native_openxr.dll` and `nvngx.dll_gtavxr_sr.dll` remain in the verified upstream runtime directory. The normal launch uses them, with no FSR provider or OptiScaler injection.

For the FSR experiment, Linux v1.7 creates two **per-session** directories:

- `fsr-runtime/` holds a private copy of the upstream bridge and an alternate `nvngx.dll_gtavxr_sr.dll` built from `code/bridge/fsr_forwarder.cpp`.
- `fsr-provider/` holds a private copy of the user's OptiScaler, its generated configuration and a user-supplied NGX model copied as `nvngx.dll`. Remaining backend DLLs are linked from the user's extracted OptiScaler package.

The launcher points `GTAVXR_BRIDGE_PATH` to the private bridge only during `--fsr` launch and gives the alternate forwarder `GTAVXR_FSR_PROVIDER_PATH` so it can load OptiScaler's `NVSDK_NGX_D3D12_*` exports.

This is a **bridge-level provider substitution**, not a native FidelityFX SDK integration. AMD FSR 3/4 activation under Proton, performance and stereo quality remain unverified. A true standalone AMD SDK path would need further native D3D12 integration and its own tests. The separate compiled forwarder can be built on Windows x64; see [source and build instructions](../../code/bridge/fsr-forwarder/README.md).

Linux v1.6's earlier temporary `winmm.dll` files are recovered on the next normal launch, if an interrupted v1.6 session left a journal in the game directory. The v1.7 method does not stage any new files in the GTA V directory.

The official upstream payload, patched game executable and proprietary AMD/NVIDIA binaries are **not** distributed by this repository.
