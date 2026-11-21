# Experimental FSR bridge forwarder

This folder builds a Windows x64 DLL for the Linux launcher's `--fsr 3` and `--fsr 4` test. It uses GTAVXR's existing D3D12 NGX input interface to ask [OptiScaler](https://github.com/optiscaler/OptiScaler) to use FSR. It does **not** bundle or implement AMD's FidelityFX SDK directly.

The original `nr_forwarder.cpp`, `gtavxr_native_openxr.dll`, and upstream DLSS forwarder remain unchanged. Only an opt-in VR session uses this alternate DLL in its isolated session runtime.

Build on Windows x64 with Visual Studio 2022 and the Windows SDK:

```powershell
cmake -S code/bridge/fsr-forwarder -B build/fsr-forwarder -A x64
cmake --build build/fsr-forwarder --config Release
```

The output is `build/fsr-forwarder/Release/nvngx.dll_gtavxr_sr.dll`. It is also published as a GitHub Actions artifact by `fsr-forwarder.yml`.

The caller provides `GTAVXR_FSR_PROVIDER_PATH` as a Windows path to a local, user-supplied `OptiScaler.dll`. This forwarding path needs a live test under Proton before it can be called working FSR. FSR 4 additionally needs the appropriate AMD runtime components; merely setting `PROTON_FSR4_UPGRADE=1` does not install them.

The first test must confirm `EYE_CHAIN state=chain ... sr=1` and `EYE_CHAIN pair ... left_sr=1 ... right_sr=1` in GTAVXR's OpenXR log, then confirm OptiScaler's chosen output backend and inspect both eyes for correct motion and ghosting. A DLL loading successfully is not proof of FSR operation.
