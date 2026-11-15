# Install, update, or remove GTAVXR

Use **GTA V Legacy 1.0.3889.0** on 64-bit Windows. Download **GTAVXR.exe** from the official Releases page. One Suite handles setup, profiles, maintenance, and launch. [Download GTAVXR](https://github.com/LVL-VR/GTAVXR/releases/latest) · [Check compatibility](COMPATIBILITY.md)

| What you want to do | Where to start |
| --- | --- |
| Play GTAVXR for the first time | [Install and play](#install-and-play) |
| Move from 1.0.0 to 1.0.2 with your progress intact | [Update and keep your data](#update-and-keep-your-data) |
| Take GTAVXR out of the game and keep your VR profiles | [Uninstall from the game](#uninstall-from-the-game) |
| Delete the Suite and its data or start over | [Remove GTAVXR completely](#remove-gtavxr-completely) |
| Fix a moved game, missing files, or an interrupted install | [Repair and recover](#repair-and-recover) |

## Install and play

1. Run **GTAVXR.exe** as administrator for installation. If prompted, choose the Legacy folder that contains **GTA5.exe**. You can choose a different drive for **Suite data** before continuing.
2. Select **Install GTAVXR**. The Suite checks Legacy files and applies the included patch locally. It creates a **VR Story** profile and copies the eligible regular GTA saves it finds. In the profile's **Save** tab, select a save or **Start a new story**.
3. Close the elevated Suite and reopen it normally. Use **Settings → Headset → Change** to select the runtime for your connection, or use **Automatic** to follow Windows. With the headset connected, select your profile and press **Play**.
4. Start at **Franklin and Lamar** if you have a save after the prologue. Save inside GTA when you finish and follow the closing instructions. [First session](FIRST_SESSION.md) · [Choose a save](SAVES.md) · [Controls](VR_CONTROLS.md)

## Update and keep your data

1. Close GTA and the old Suite. Download the **1.0.2 GTAVXR.exe** from Releases and run it as administrator with the Windows account you used for 1.0.0.
2. Open the existing library. If you moved it, select **Locate Suite data** when prompted and choose the library folder containing `settings.json`. If two libraries contain different progress, review both and import the missing profiles from the other library when prompted.
3. Select **Update GTAVXR**. This upgrades the existing installation and moves eligible 1.0.0 profiles to 1.0.2 in place. Saves, profile names and settings, and your mod library are kept. A mod that needs attention remains in the library. The Suite reports any compatibility decision before launching.
4. Open the updated launcher normally. Verify that the profile and save you want appear before launching. The update retires the identified previous public game files and refreshes the official launcher at its installed location. For a 1.0.0 executable you kept elsewhere, open **Settings → Portable 1.0.0 copy** and select that file to replace or remove it. Use the launcher you intend to keep for future play.

If you already removed 1.0.0 from the game but kept its Suite library, open 1.0.2 and point it at that library. You can also do this if you lost the old launcher. If an update is interrupted, complete **Fix now** when offered, then retry the update.

For later versions, **Settings → Check for updates** opens the official GitHub release. It can verify the downloaded file when the release provides a SHA-256. Close the old Suite before opening the new EXE. [Suite and profiles](SUITE.md)

## Uninstall from the game

Close GTA and allow the Suite to finish restoring normal gameplay files. Open **Settings → GTAVXR in the game → Uninstall**. This removes the managed GTAVXR game files and keeps your Suite profiles, VR saves, settings, and imported mods for a later reinstall.

## Remove GTAVXR completely

1. Close GTA and finish any **Fix now** recovery or pending update. If the game folder still needs administrator access, reopen the Suite as administrator.
2. In **Settings**, select **Remove GTAVXR completely**. Review the listed locations. Confirm only when you are ready to delete the VR saves, profiles, settings, mod library, session files and backups, and the identified launcher and shortcuts.
3. Wait for the launcher to close and complete its cleanup. Files you downloaded or copied to unrelated folders are yours to remove separately. Use **Portable 1.0.0 copy** before removal to identify an old portable launcher. Preserve **Documents → Rockstar Games → GTA V** for regular GTA saves and settings.
4. To start over, download the current **GTAVXR.exe** again and follow [Install and play](#install-and-play). The initial profile can import regular GTA saves. Select **Start a new story** if you want a fresh campaign too.

If you already deleted GTA, complete removal can still clean the Suite when it can verify the game is gone. Reconnect a missing drive if asked. If the Suite lists unfamiliar files or recovered player files, move the named files to a location you choose before retrying. Use **Uninstall** above when you want to retain VR progress.

## Repair and recover

- **Interrupted install or session.** With GTA closed, select **Fix now**. Finish recovery before retrying installation or removing the Suite library.
- **Access is denied.** Open the Suite as administrator for writes to the game folder. [Installation recovery](TROUBLESHOOTING.md#access-denied-during-installation)
- **GTAVXR files are missing or changed.** Use **Settings → Check files** with GTA closed. If the report names a required Legacy file, follow the troubleshooting instructions for that file.
- **GTA moved.** Select the new complete Legacy folder under **Settings → Game → Change**. The Suite checks the base game and any files it previously installed before adopting that folder. A second, still-present Legacy installation can be uninstalled separately. Reconnect the old drive if recovery needs it.
- **Suite data moved.** Use **Locate Suite data** when the stored path is unavailable. Keep the library intact until recovery finishes. [Find where Suite data is stored](SUITE.md#choose-where-the-suite-stores-its-data)

