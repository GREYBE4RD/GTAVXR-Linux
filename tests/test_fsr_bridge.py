"""Offline tests for the opt-in FSR provider and original-launcher isolation."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gtavxr_linux", ROOT / "gtavxr-linux.py")
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


def fake_pe(path, marker=b"A"):
    payload = bytearray(512)
    payload[:2] = b"MZ"
    payload[0x3c:0x40] = (128).to_bytes(4, "little")
    payload[128:132] = b"PE\x00\x00"
    payload[132:134] = (0x8664).to_bytes(2, "little")
    payload[-1:] = marker
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


class FsrBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.game = root / "game"
        self.game.mkdir()
        self.source = root / "opti"
        self.source.mkdir()
        self.model_dir = root / "dlss"
        self.model_dir.mkdir()
        self.runtime = root / "upstream_runtime"
        self.runtime.mkdir()
        self.session = root / "session"
        fake_pe(self.source / "OptiScaler.dll", b"O")
        fake_pe(self.source / "amd_fidelityfx_loader_dx12.dll", b"A")
        fake_pe(self.model_dir / "nvngx_dlss.dll", b"N")
        fake_pe(self.runtime / "nvngx.dll_gtavxr_sr.dll", b"D")
        fake_pe(self.runtime / "gtavxr_native_openxr.dll", b"B")
        self.alt = fake_pe(root / "built" / "nvngx.dll_gtavxr_sr.dll", b"F")
        self.ini = ("[Upscalers]\nDx11Upscaler=auto\nDx12Upscaler=auto\n"
                    "[FrameGen]\nEnabled=auto\nFGInput=auto\nFGOutput=auto\n"
                    "[FSR]\nFsr4Update=auto\n")
        (self.source / "OptiScaler.ini").write_text(self.ini)
        self.args = SimpleNamespace(fsr="3", optiscaler_dir=self.source,
                                    fsr_dlss_dir=self.model_dir,
                                    fsr_forwarder=self.alt)

    def test_separate_provider_staged_without_touching_originals(self):
        before_bridge = (self.runtime / "gtavxr_native_openxr.dll").read_bytes()
        before_dlss = (self.runtime / "nvngx.dll_gtavxr_sr.dll").read_bytes()
        inputs = APP.fsr_bridge_inputs(self.args, self.game, self.runtime)
        APP.fsr_stage_bridge(inputs, self.runtime, self.session)
        self.assertEqual((self.runtime / "gtavxr_native_openxr.dll").read_bytes(), before_bridge)
        self.assertEqual((self.runtime / "nvngx.dll_gtavxr_sr.dll").read_bytes(), before_dlss)
        self.assertEqual((self.session / "fsr-runtime/nvngx.dll_gtavxr_sr.dll").read_bytes(), self.alt.read_bytes())
        self.assertEqual((self.session / "fsr-provider/nvngx.dll").read_bytes(),
                         (self.model_dir / "nvngx_dlss.dll").read_bytes())
        self.assertTrue((self.session / "fsr-provider/amd_fidelityfx_loader_dx12.dll").is_symlink())
        cfg = (self.session / "fsr-provider/OptiScaler.ini").read_text()
        self.assertIn("Dx11Upscaler=fsr31", cfg)
        self.assertIn("Dx12Upscaler=fsr31", cfg)
        self.assertIn("Enabled=false", cfg)
        self.assertIn("Fsr4Update=false", cfg)
        self.assertFalse((self.game / "winmm.dll").exists())

    def test_fsr4_requests_sdk_upgrade_without_frame_generation(self):
        self.args.fsr = "4"
        inputs = APP.fsr_bridge_inputs(self.args, self.game, self.runtime)
        self.assertIn(b"Fsr4Update=true", inputs[2])
        self.assertIn(b"Enabled=false", inputs[2])

    def test_original_dlss_forwarder_rejected(self):
        self.args.fsr_forwarder = self.runtime / "nvngx.dll_gtavxr_sr.dll"
        with self.assertRaises(APP.Failure):
            APP.fsr_bridge_inputs(self.args, self.game, self.runtime)

    def test_missing_provider_rejected(self):
        self.args.fsr_forwarder = None
        with self.assertRaises(APP.Failure):
            APP.fsr_bridge_inputs(self.args, self.game, self.runtime)

    def test_user_vr_profile_preserved(self):
        source = Path(self.tmp.name) / "vr-settings.ini"
        source.write_text("[Graphics]\nupscale=off\nneural=1\n")
        destination = Path(self.tmp.name) / "vr-settings-fsr.ini"
        APP.fsr_profile(source, destination)
        self.assertIn("upscale=off", source.read_text())
        self.assertIn("neural=1", source.read_text())
        self.assertIn("upscale=quality", destination.read_text())
        self.assertIn("neural=0", destination.read_text())


if __name__ == "__main__":
    unittest.main()
