# GTAVXR 1.0.2 source components

This release includes the public Suite, OpenXR bridge, VR support components, and Trainer source. The Suite source builds a fixture tool for local validation. For the playable installer, download GTAVXR.exe from Releases.

| Folder | Contents |
| --- | --- |
| `code/suite` | UI, profiles, installer, and tests with example files |
| `code/vr` | VR logic and math, interfaces, and Windows support |
| `code/bridge` | OpenXR bridge and graphics components, with CMake and shaders |
| `code/trainer` | Trainer source, build instructions, and notices |

The Suite includes the `--bundle-fixtures`, `--render-all`, and `--version` test commands and the `--runtime-report` local diagnostic. Use the example files to test the UI and patch application. The playable installer is available in Releases. [Third-party notices](../THIRD_PARTY_NOTICES.md)
