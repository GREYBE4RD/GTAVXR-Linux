# GTAVXR 1.0.2 compatibility

GTAVXR 1.0.2 uses **GTA V Legacy 1.0.3889.0** as its base. The Suite checks the files in your selected installation before applying the patch.

## Store support

| Store | Setup | What has been confirmed |
| --- | --- | --- |
| **Steam** | GTA V Legacy 1.0.3889.0 | Installation verified with the reference files. |
| **Rockstar Games Launcher** | GTA V Legacy, **Quest 3 and VDXR** | VR launch confirmed through the prologue. |
| **Epic Games Store** | GTA V Legacy, **Quest 3 and Virtual Desktop with VDXR** | VR gameplay confirmed, including missions and driving. |

[Installation and permission recovery](INSTALLATION.md) · [Known issues](KNOWN_ISSUES.md)

## Choose a runtime

For Quest over Virtual Desktop, start with **VDXR**. SteamVR is supported, including **Steam Link**, and can have a noticeable frame-rate cost compared with VDXR. The difference depends on resolution, GPU, encoding and runtime settings. With a wired headset or a vendor PCVR connection, choose the headset's compatible **OpenXR runtime**. VDXR and SteamVR are both implementations of OpenXR. [Graphics and performance](GRAPHICS.md)

## Components and runtimes

| Component | What the Suite supports or checks | What matters in-game |
| --- | --- | --- |
| **GTA V Legacy folder** | Detects Steam libraries and Rockstar-registered paths. You can also select a folder manually. Installation checks the base executable and required resources. | Installation, launch, and shutdown with that setup. See the store results above. |
| **OpenXR** | **Automatic** follows the active Windows runtime. You can also select a detected runtime or an installed manifest. | The XR session opens, both eyes display correctly, and tracking, controllers, and reconnection work. |
| **Headset connection** | Virtual Desktop can use VDXR or SteamVR, depending on its configuration. Steam Link uses SteamVR. Meta Link and Air Link use Meta's PC software. Select the runtime for your connection. | VDXR is confirmed in the setups above. SteamVR via Steam Link is confirmed on Quest 3 in Story Mode. Other headset and controller combinations vary. |
| **Mods and Script Host** | Inspects the mod package, requirements, and scripting APIs. | The mod loads and its actions or content work in Story Mode. |
| **DLSS, Neural Rendering, and OFXR** | Detects model files or the appropriate layer and offers fallbacks when a component is missing. | The selected mode initializes and runs with your GPU and runtime. |

When SteamVR opens the OpenXR session and both stick clicks are available, press and release **L3 + R3** with the sticks centered to open the GTAVXR menu. Press **F9** if your controller profile lacks one of the clicks. [VR controls](VR_CONTROLS.md)

If your setup has a problem, record the store, version, GPU, headset, connection, and runtime you used. [Troubleshooting](TROUBLESHOOTING.md)

For help connecting your headset, see the vendor documentation. [Steam Link](https://help.steampowered.com/en/faqs/view/0E2C-406B-9135-38A4) · [Meta Horizon Link OpenXR runtime](https://developers.meta.com/vr/documentation/unity/unity-link/#activate-openxr-runtime)
