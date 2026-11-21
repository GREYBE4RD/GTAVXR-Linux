#!/usr/bin/env python3
"""GTAVXR Linux installer and VR launcher v1.10.

Downloads and verifies official GTAVXR.exe 1.0.5 if no local payload exists,
then extracts its embedded release ZIP without executing the Windows installer.
GTA V Legacy 1.0.3889.0 resources are reconstructed with rage-cli + libzstd.

No command: detect the game and Proton, offer first installation, and launch.
Missing local payload: securely fetch and unpack the official v1.0.5 EXE.
update:     safely upgrade an existing 1.0.2 Linux installation to 1.0.5.
verify:     reconstruct/hash-check files in a disposable temporary directory.
install:    install verified game files and runtime without replacing retail files.
repair:     reconstruct missing installer-owned files without overwriting changes.
status:     check installed files, Proton, and the SteamVR runtime.
launch:     launch GTAVXR through Proton using a separate VR prefix.
import-saves: copy missing normal GTA V Story Mode saves into the VR prefix.
steamvr-status / steamvr-patch / steamvr-restore: manage a version-locked
    SteamVR 2.19.3 Vulkan descriptor-pool workaround.
uninstall:  remove only hash-verified installer-owned files.

The VR prefix keeps normal GTA V saves and settings separate. Imported saves
are copied, never moved, and VR progress is not overwritten. SteamVR patching
is permitted only for the exact verified compositor build and when it is closed.
"""
import argparse
from datetime import datetime, timezone
import fcntl
from contextlib import contextmanager
import ctypes
import ctypes.util
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
from urllib import error as urlerror, request as urlrequest
from urllib.parse import urlsplit
import zipfile

RELEASE = "gtavxr-1-0-5"
PREVIOUS_RELEASE = "gtavxr-1-0-2"
BASE_SHA = "677E4E355CFBDB13273B1D992407E3C261B3A108DC4DD5C8A0C4C1DA651802E5"
TARGET_SHA = "A6776E715859B9299A2951018FE639198FA7B7CCEA5322985B6A06C99ABE390D"
DEFAULT_GAME = Path("/mnt/linflux/SteamLibrary/steamapps/common/Grand Theft Auto V")
DEFAULT_PAYLOAD = Path.home() / "Downloads/GTAVXR-payload-v1.0.5.zip"
STATE_FILE = "gtavxr-linux-state-v1.json"
RAGE_DEFAULT = Path.home() / '.local/bin/rage'
PROTON_DEFAULT = Path('/mnt/linflux/SteamLibrary/steamapps/common/Proton 11.0/proton')
STEAM_DEFAULT = Path.home() / '.local/share/Steam'
DATA_ROOT = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'gtavxr-linux'
APP_ID = '271590'
VERSION = '1.10'
# Pinned to the official LVL-VR GTAVXR 1.0.5 release asset. Do not use /latest:
# later releases need their own identity, payload manifest and installer support.
UPSTREAM_EXE_URL = 'https://github.com/LVL-VR/GTAVXR/releases/download/v1.0.5/GTAVXR.exe'
UPSTREAM_EXE_SHA = '83469b72c10f2d35f9f6025c4e31c75ae7632e413165b46343749de5a31fff7c'
UPSTREAM_EXE_BYTES = 25691648
# The embedded ZIP is authenticated by the SHA-256 of the complete official
# Windows EXE above. Its compressed size can change independently of the game.
# Keep the manifest identity and upstream source file inventory pinned.
UPSTREAM_PAYLOAD_COUNT = 1101
UPSTREAM_RUNTIME_FILES = frozenset({
    'GTAVXRHost.dll', 'gtavxr_native_openxr.dll', 'gtavxr_trainer.dll',
    'openxr_loader.dll', 'nvngx.dll_gtavxr.dll', 'nvngx.dll_gtavxr_sr.dll',
    'scripthost/ScriptHookVDotNet.asi', 'scripthost/ScriptHookVDotNet2.dll',
    'scripthost/ScriptHookVDotNet3.dll', 'scripthost/ScriptHookVDotNet.ini',
    'scripthost/gtavxr-host-features.txt',
    'scripthost/ScriptHookVDotNet.gtavxr-memory.txt',
    'scripthost/ScriptHookVDotNet-LICENSE.txt',
    'scripthost/ScriptHookVDotNet-THIRD-PARTY-NOTICES.md',
})
MAX_EXE_BYTES = 64 * 1024 * 1024
STEAMVR_ORIGINAL_SHA = 'b3747b541c86f683286f13fcce9ed7761e0258ecef3827c5ce915167226947fe'
STEAMVR_PATCHED_SHA = 'e16e01eefa44ed709a00aaf1617538f595def0d1805d9674349c9c380dd1e813'
STEAMVR_PATCH_EDITS = (
    (0x4365b9, 'be80380100'),    # UNIFORM_BUFFER: 1600 -> 80000
    (0x4365c8, 'be409c0000'),    # SAMPLER: 800 -> 40000
    (0x4365df, 'be00710200'),    # SAMPLED_IMAGE: 3200 -> 160000
    (0x4365f2, 'be00710200'),    # STORAGE_IMAGE: 3200 -> 160000
    (0x436613, 'b910270000'),    # maxSets: 200 -> 10000
)


class Failure(Exception):
    pass

def check(cond, message):
    if not cond:
        raise Failure(message)

def digest(data):
    return hashlib.sha256(data).hexdigest().upper()

def check_bytes(data, entry, name):
    check(len(data) == entry['bytes'], f"Size mismatch: {name}")
    check(digest(data) == entry['sha256'].upper(), f"SHA256 mismatch: {name}")
    return data

def safe_rel(name):
    p = PurePosixPath(name)
    check(bool(name) and not name.startswith('/') and not name.startswith('\\') and '\\' not in name and ':' not in name and all(x not in ('.','..') for x in name.split('/')), f"Unsafe manifest path: {name}")
    return Path(*p.parts)

def no_symlinks(root, rel):
    p = root
    for part in rel.parts:
        p = p / part
        check(not p.is_symlink(), f"Refusing symbolic link: {p}")
    return p

def libzstd():
    libname = ctypes.util.find_library('zstd')
    check(libname is not None, "libzstd not found. Install the zstd package.")
    lib = ctypes.CDLL(libname)
    lib.ZSTD_createDCtx.restype = ctypes.c_void_p
    lib.ZSTD_freeDCtx.argtypes = [ctypes.c_void_p]
    lib.ZSTD_decompress_usingDict.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    lib.ZSTD_decompress_usingDict.restype = ctypes.c_size_t
    lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
    lib.ZSTD_isError.restype = ctypes.c_uint
    return lib

def zstd_with_dictionary(frame, basis, size, lib):
    check(0 < size <= 64 * 1024 * 1024, "Unexpected decompressed size")
    out = ctypes.create_string_buffer(size)
    src = ctypes.create_string_buffer(frame)
    dictionary = ctypes.create_string_buffer(basis)
    ctx = lib.ZSTD_createDCtx()
    check(bool(ctx), "Cannot create zstd context")
    try:
        n = lib.ZSTD_decompress_usingDict(ctx, out, size, src, len(frame), dictionary, len(basis))
        check(not lib.ZSTD_isError(n) and n == size, "Zstd dictionary decompression failed")
        return out.raw[:n]
    finally:
        lib.ZSTD_freeDCtx(ctx)

def read_manifest(z):
    manifest = json.loads(z.read('manifest.json'))
    check(manifest['schema'] == 'gtavxr-embedded-release-v2' and manifest['id'] == RELEASE, "Unexpected release manifest")
    check(manifest['base']['sha256'].upper() == BASE_SHA and manifest['target']['sha256'].upper() == TARGET_SHA, "Executable identity mismatch")
    check(len(manifest['entries']) == UPSTREAM_PAYLOAD_COUNT + len(UPSTREAM_RUNTIME_FILES) + 4,
          "Unexpected manifest entry count")
    from collections import Counter
    kinds = Counter(e['kind'] for e in manifest['entries'])
    check(kinds == {'payload': UPSTREAM_PAYLOAD_COUNT,
                    'runtime': len(UPSTREAM_RUNTIME_FILES), 'metadata': 2,
                    'patch': 1, 'codec': 1}, 'Unexpected payload kind inventory')
    check({e['path'] for e in manifest['entries'] if e['kind'] == 'runtime'} ==
          UPSTREAM_RUNTIME_FILES, 'Required GTAVXR runtime files differ from upstream')
    names = set()
    for e in manifest['entries']:
        safe_rel(e['path'])
        check(e['path'] not in names, "Duplicate manifest path")
        names.add(e['path'])
    return manifest

def read_zip(z, name, entry):
    return check_bytes(z.read(name), entry, name)

def needs_rpf(manifest):
    return [e for e in manifest['entries'] if e.get('retail_archive')]

def source_file(root, e):
    archive = safe_rel(e['retail_archive'])
    entry = safe_rel(e['retail_entry'])
    return no_symlinks(root, archive / entry)

def asset_from_rpf(root, e):
    f = source_file(root, e)
    check(f.is_file(), f"Missing extracted retail file: {f}")
    reference = e.get('retail_base') or e
    check(f.stat().st_size == reference['bytes'], f"Unexpected retail file size: {f}")
    return check_bytes(f.read_bytes(), reference, str(f))

def extract_with_rage(root, entries, game, rage):
    """Read-only extraction of all necessary retail archive members into temp."""
    rage_bin = str(rage)
    if os.path.sep not in rage_bin:
        resolved = shutil.which(rage_bin)
        check(resolved is not None, f"rage-cli executable not found: {rage_bin}")
        rage_bin = resolved
    else:
        check(Path(rage_bin).is_file(), f"rage-cli executable not found: {rage_bin}")

    by_archive = {}
    for e in entries:
        if not e.get('retail_archive'):
            continue
        archive = e['retail_archive']
        member = e['retail_entry']
        safe_rel(archive)
        safe_rel(member)
        check(archive in ('common.rpf', 'update/update2.rpf'), f"Unexpected retail archive: {archive}")
        by_archive.setdefault(archive, set()).add(member)

    for archive, members in sorted(by_archive.items()):
        path = no_symlinks(game, safe_rel(archive))
        check(path.is_file(), f"Required GTA archive missing: {path}")
        out = root / safe_rel(archive)
        out.mkdir(parents=True, exist_ok=False)
        print(f"Extracting {len(members)} original members from {archive} with rage-cli...", flush=True)
        command = [rage_bin, '--no-update-check', '--exe', str(game / 'GTA5.exe'),
                   'extract', str(path), *sorted(members), '-o', str(out)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError as error:
            raise Failure(f"Cannot run rage-cli: {error}") from error
        if result.returncode != 0:
            details = (result.stdout + '\n' + result.stderr).strip()
            raise Failure(f"rage-cli failed extracting {archive} (exit {result.returncode}):\n{details[-3500:]}")
        print(f"  Extraction finished for {archive}. Validating original hashes...", flush=True)


class VerifiedHTTPSRedirect(urlrequest.HTTPRedirectHandler):
    """Do not follow non-HTTPS redirects for the pinned GitHub asset."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urlsplit(newurl)
        check(url.scheme == 'https' and url.hostname in
              ('github.com', 'release-assets.githubusercontent.com',
               'objects.githubusercontent.com'),
              f'Refusing unexpected release download redirect: {newurl}')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def verify_upstream_exe(path):
    check(path.is_file() and not path.is_symlink(), f'Official GTAVXR.exe not found: {path}')
    check(path.stat().st_size == UPSTREAM_EXE_BYTES,
          f'GTAVXR.exe size mismatch: expected {UPSTREAM_EXE_BYTES} bytes')
    check(file_sha_lower(path) == UPSTREAM_EXE_SHA,
          'GTAVXR.exe SHA-256 mismatch; this is not the pinned official 1.0.5 release')
    print('GTAVXR: Official Windows release SHA-256 verified.', flush=True)


def download_upstream_exe(destination):
    """Download into an isolated temporary directory and verify before parsing."""
    print('GTAVXR: Downloading official GTAVXR 1.0.5 release...', flush=True)
    req = urlrequest.Request(UPSTREAM_EXE_URL,
                             headers={'User-Agent': 'GTAVXR-Linux/1.5',
                                      'Accept': 'application/octet-stream'})
    opener = urlrequest.build_opener(VerifiedHTTPSRedirect())
    written = 0
    next_notice = 4 * 1024 * 1024
    try:
        with opener.open(req, timeout=45) as response, destination.open('xb') as stream:
            final_url = urlsplit(response.geturl())
            check(final_url.scheme == 'https', 'Release download was not HTTPS')
            length = response.headers.get('Content-Length')
            if length is not None:
                check(0 < int(length) <= MAX_EXE_BYTES,
                      'Unexpected official release download size')
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                check(written <= MAX_EXE_BYTES, 'Official release download is too large')
                stream.write(chunk)
                if written >= next_notice:
                    print(f'  downloaded {written // (1024 * 1024)} MiB...', flush=True)
                    next_notice += 4 * 1024 * 1024
            stream.flush()
            os.fsync(stream.fileno())
    except (urlerror.URLError, TimeoutError) as error:
        raise Failure(f'Cannot download the official GTAVXR release: {error}. '
                      'Use --installer /path/to/GTAVXR.exe or --payload /path/to/GTAVXR-payload.zip.') from error
    check(written == UPSTREAM_EXE_BYTES, f'Official GTAVXR.exe download truncated ({written} bytes)')
    verify_upstream_exe(destination)


def embedded_release_zip(image):
    """Find the raw ZIP manifest resource in a .NET PE using its ZIP directory.

    The official Windows Suite embeds the release as an uncompressed .NET
    manifest resource. Scan valid ZIP EOCD records; account for PE bytes before
    and after the ZIP, without running an EXE or invoking a Windows extractor.
    """
    signature = b'PK\x05\x06'
    i = image.rfind(signature)
    while i >= 0:
        if i + 22 <= len(image):
            (_, disk, cd_disk, disk_records, total_records,
             cd_size, cd_offset, comment_len) = struct.unpack_from('<4s4H2LH', image, i)
            start = i - cd_size - cd_offset
            end = i + 22 + comment_len
            if (disk == cd_disk == 0 and disk_records == total_records and
                    300 <= total_records <= 800 and comment_len == 0 and
                    10 * 1024 * 1024 <= end - start <= 40 * 1024 * 1024 and
                    0 <= start < i and end <= len(image) and
                    image[start:start + 4] == b'PK\x03\x04' and
                    image[start + cd_offset:start + cd_offset + 4] == b'PK\x01\x02'):
                archive = image[start:end]
                # Byte identity is inherited from the verified official EXE;
                # reject any embedded ZIP that lacks the pinned release manifest.
                with zipfile.ZipFile(io.BytesIO(archive)) as z:
                    check(z.testzip() is None, 'Embedded release ZIP failed CRC verification')
                    read_manifest(z)
                return archive
        i = image.rfind(signature, 0, i)
    raise Failure('Could not find the GTAVXR 1.0.5 embedded release ZIP inside the verified EXE')


@contextmanager
def acquire_payload(args):
    """Use a local ZIP, a verified local EXE, or a verified official download."""
    if args.installer is None and args.payload.is_file():
        print(f'GTAVXR: Using existing payload: {args.payload}', flush=True)
        yield args.payload
        return
    if args.installer is None and getattr(args, 'payload_explicit', False):
        raise Failure(f'Specified payload not found: {args.payload}')
    check(args.installer is not None or not args.no_download,
          f'Payload not found: {args.payload}. Remove --no-download to fetch the official release.')
    with tempfile.TemporaryDirectory(prefix='gtavxr-release-') as temp:
        root = Path(temp)
        exe = args.installer if args.installer is not None else root / 'GTAVXR.exe'
        if args.installer is not None:
            verify_upstream_exe(exe)
        else:
            download_upstream_exe(exe)
        print('GTAVXR: Extracting verified embedded release ZIP...', flush=True)
        bundle = embedded_release_zip(exe.read_bytes())
        payload = root / 'GTAVXR-payload.zip'
        with payload.open('xb') as output:
            output.write(bundle)
            output.flush()
            os.fsync(output.fileno())
        print('GTAVXR: Embedded payload verified; temporary files will be removed after installation.', flush=True)
        yield payload


def stage(args):
    """Use an explicitly matching local payload, or fetch and extract 1.0.5."""
    # Repair with no missing files should not cause a network download.
    if args.command == 'repair':
        game, runtime, state = installed(args, verify=False)
        missing = 0
        for info in state['files']:
            root = runtime if info['kind'] in ('runtime', 'metadata') else game
            target = no_symlinks(root, safe_rel(info['path']))
            if target.exists():
                check(file_matches(target, info),
                      f'Refusing to overwrite a modified installer-owned file: {target}')
            else:
                missing += 1
        if not missing:
            print('GTAVXR: All installer-owned files are already present and verified.')
            return
    with acquire_payload(args) as payload:
        stage_verified_payload(args, payload)


def stage_verified_payload(args, payload):
    game = args.game.resolve()
    check(game.is_dir(), f"Game directory not found: {game}")
    check(not args.game.is_symlink(), "Game directory is a symlink")
    repairing = args.command == 'repair'
    upgrading = args.command == 'update'
    current = None
    missing = set()
    if repairing:
        _, current_runtime, current = installed(args, verify=False)
        for info in current['files']:
            root = current_runtime if info['kind'] in ('runtime', 'metadata') else game
            dest = no_symlinks(root, safe_rel(info['path']))
            if dest.exists():
                check(file_matches(dest, info),
                      f'Refusing to overwrite an existing modified file: {dest}')
            else:
                missing.add((info['kind'], info['path']))
        if not missing:
            print('GTAVXR: All installer-owned files are already present and verified.')
            return
        print(f'GTAVXR: Reconstructing {len(missing)} missing files for safe repair.', flush=True)
    elif upgrading:
        _, previous_runtime, current = installed(args, verify=True, allow_older=True)
        check(current['release'] == PREVIOUS_RELEASE,
              'Only verified 1.0.2 installations can be upgraded to 1.0.5')
        check(not process_running('GTAVXR_SourceBaseline.exe'),
              'Close GTAVXR completely before upgrading')
        print(f'GTAVXR: Upgrading {PREVIOUS_RELEASE} to {RELEASE}; saves and VR settings remain intact.', flush=True)
    else:
        check(not (game / STATE_FILE).exists(), "Existing Linux installation state found. Use 'repair' or 'update'.")
    check(payload.is_file(), f"Payload not found: {payload}")
    if args.rpf_dir is not None:
        check(args.rpf_dir.is_dir(), f"Extracted resource directory not found: {args.rpf_dir}")
        rpf_location = args.rpf_dir.resolve()
        check(not (rpf_location == game or game in rpf_location.parents), "Extract retail resources outside GTA's installation folder")
    else:
        rpf_location = None
    if not repairing and not upgrading:
        check(not any((game / x).exists() for x in ('GTAVXR_SourceBaseline.exe','gtavxr_native_openxr.dll')), "An existing GTAVXR installation is present; refusing to overwrite")
    exe = game / 'GTA5.exe'
    check(exe.is_file(), "GTA5.exe not found")
    check(exe.stat().st_size == 47467128, "GTA5.exe has the wrong file size")
    retail_bytes = exe.read_bytes()
    check(digest(retail_bytes) == BASE_SHA, "GTA5.exe does not match required 3889 retail binary")
    with zipfile.ZipFile(payload) as z:
        check(z.testzip() is None, "ZIP verification failed")
        manifest = read_manifest(z)
        entries = manifest['entries']
        resources = needs_rpf(manifest)
        print(f"Verified GTA V Legacy and {RELEASE} payload. Need {len(resources)} retail resource references.", flush=True)
        with tempfile.TemporaryDirectory(prefix='gtavxr-linux-') as temp:
            tmp = Path(temp)
            source_root = rpf_location
            if source_root is None:
                source_root = tmp / 'retail'
                source_root.mkdir()
                extract_with_rage(source_root, resources, game, args.rage)
            # Validate ALL original inputs before writing to the game folder.
            for index, e in enumerate(resources, 1):
                asset_from_rpf(source_root, e)
                if index % 200 == 0:
                    print(f"  verified {index}/{len(resources)}", flush=True)
            print('Retail resources verified. Reconstructing to a temporary staging directory...', flush=True)
            lib = libzstd()
            output = tmp / 'stage'
            output.mkdir()
            files = []
            for index, e in enumerate(entries, 1):
                kind = e['kind']
                if kind in ('patch','codec'):
                    continue
                rel = safe_rel(e['path'])
                if e.get('shader_patch'):
                    basis = asset_from_rpf(source_root, e) if e.get('retail_archive') else b''
                    patch_name = 'shader-deltas/' + e['path'] + '.zst'
                    delta = read_zip(z, patch_name, e['shader_patch'])
                    data = zstd_with_dictionary(delta, basis, e['bytes'], lib)
                elif e.get('retail_archive'):
                    data = asset_from_rpf(source_root, e)
                else:
                    data = read_zip(z, e['path'], e)
                check_bytes(data, e, e['path'])
                dest = output / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                files.append({'path':str(rel),'sha256':e['sha256'].upper(),'bytes':e['bytes'],'kind':kind})
                if index % 300 == 0:
                    print(f"  reconstructed {index}/{len(entries)}", flush=True)
            patch = next(e for e in entries if e['kind'] == 'patch')
            target = zstd_with_dictionary(read_zip(z, patch['path'], patch), retail_bytes, manifest['target']['bytes'], lib)
            check_bytes(target, manifest['target'], 'GTAVXR_SourceBaseline.exe')
            (output / 'GTAVXR_SourceBaseline.exe').write_bytes(target)
            files.append({'path':'GTAVXR_SourceBaseline.exe','sha256':TARGET_SHA,'bytes':len(target),'kind':'payload'})
            if upgrading:
                upgrade_installation(args, output, files, current)
                return
            if repairing:
                check([(f['path'], f['sha256'], f['bytes'], f['kind']) for f in files] ==
                      [(f['path'], f['sha256'], f['bytes'], f['kind']) for f in current['files']],
                      'Repair content differs from the existing installation state')
            else:
                check(not any((game / x['path']).exists() for x in files if x['kind'] == 'payload'), "Installation conflicts with existing game files")
            if args.command == 'verify':
                print(f"PASS: reconstructed and verified {len(files)} files without modifying GTA V.", flush=True)
                return
            # Place runtime components outside GTA, as upstream does. Other files are game-local.
            runtime = game.parent / '.gtavxr-linux-runtime'
            if not repairing:
                check(not runtime.exists(), "Runtime directory already exists; refusing to overwrite")
            paths = []
            if not repairing:
                check(not (game / STATE_FILE).exists(), "State file already exists")
            # Check all destinations before the first file is copied.
            planned = []
            for f in files:
                rel = safe_rel(f['path'])
                destroot = runtime if f['kind'] in ('runtime', 'metadata') else game
                dest = no_symlinks(destroot, rel)
                if repairing and (f['kind'], f['path']) not in missing:
                    continue
                check(not dest.exists(), f"Refusing to overwrite: {dest}")
                check(not any(parent.is_file() for parent in dest.parents if parent != Path('/')), f"Parent is a file: {dest}")
                planned.append((output / rel, dest))
            try:
                if not repairing:
                    runtime.mkdir()
                for src, dest in planned:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    paths.append(dest)  # Include a partially copied file in rollback.
                    shutil.copyfile(src, dest)
                if not repairing:
                    state = {'schema': 'gtavxr-linux-v1', 'release': RELEASE,
                             'runtime': str(runtime), 'files': files}
                    atomic_json(game / STATE_FILE, state)
                else:
                    installed(args, verify=True)
            except BaseException:
                for path in reversed(paths):
                    path.unlink(missing_ok=True)
                if not repairing:
                    shutil.rmtree(runtime, ignore_errors=True)
                raise
            if repairing:
                print(f'GTAVXR: Repaired {len(paths)} missing files; all installed files verified.')
            else:
                print(f'GTAVXR: Installed {len(files)} verified files.')



def upgrade_journal(args):
    return args.game.resolve() / 'gtavxr-linux-upgrade-v1.json'


def upgrade_backup(args):
    return args.game.resolve().parent / '.gtavxr-linux-upgrade-backup'


def owned_destination(game, runtime, info):
    rel = safe_rel(info['path'])
    root = runtime if info['kind'] in ('runtime', 'metadata') else game
    return no_symlinks(root, rel)


def atomic_copy_into(source, destination):
    """Install a verified source using a same-directory temporary file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.gtavxr-install-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as target, source.open('rb') as original:
            shutil.copyfileobj(original, target)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(name, stat.S_IMODE(source.stat().st_mode))
        os.replace(name, destination)
    finally:
        Path(name).unlink(missing_ok=True)


def rollback_upgrade(args):
    """Recover only verified files managed by the Linux installer."""
    journal_path = upgrade_journal(args)
    check(journal_path.is_file() and not journal_path.is_symlink(),
          'No trustworthy upgrade journal found')
    record = json.loads(journal_path.read_text())
    check(record.get('schema') == 'gtavxr-linux-upgrade-v1' and
          record.get('previous', {}).get('release') == PREVIOUS_RELEASE and
          record.get('next_release') == RELEASE, 'Unrecognised upgrade journal')
    game = args.game.resolve()
    runtime = game.parent / '.gtavxr-linux-runtime'
    check(record['previous'].get('runtime') == str(runtime),
          'Upgrade journal references an unexpected runtime directory')
    backup = upgrade_backup(args)
    check(backup.is_dir() and not backup.is_symlink(),
          f'Upgrade backup missing: {backup}. No files were deleted.')
    old_files = record['previous']['files']
    new_files = record['next_files']
    old = {owned_destination(game, runtime, f): f for f in old_files}
    new = {owned_destination(game, runtime, f): f for f in new_files}
    check(len(old) == len(old_files) and len(new) == len(new_files),
          'Duplicate upgrade file destinations')
    # Verify every backup and target BEFORE changing installed files.
    for dest, info in old.items():
        section = 'runtime' if info['kind'] in ('runtime', 'metadata') else 'game'
        saved = no_symlinks(backup, Path(section) / safe_rel(info['path']))
        check(file_matches(saved, info), f'Upgrade backup damaged: {saved}')
        if dest.exists():
            check(file_matches(dest, info) or
                  (dest in new and file_matches(dest, new[dest])),
                  f'Unexpectedly modified file, refusing rollback: {dest}')
    for dest, info in new.items():
        if dest not in old and dest.exists():
            check(file_matches(dest, info),
                  f'Unexpectedly modified new file, refusing rollback: {dest}')
    for dest, info in new.items():
        if dest not in old:
            dest.unlink(missing_ok=True)
    for dest, info in old.items():
        if not file_matches(dest, info):
            section = 'runtime' if info['kind'] in ('runtime', 'metadata') else 'game'
            saved = backup / section / safe_rel(info['path'])
            atomic_copy_into(saved, dest)
    state_path = game / STATE_FILE
    pending = state_path.with_name(state_path.name + '.tmp')
    check(not pending.is_symlink(), f'Unsafe state temporary file: {pending}')
    if pending.exists():
        pending.unlink()
    atomic_json(state_path, record['previous'])
    installed(args, verify=True, allow_older=True)
    journal_path.unlink()
    shutil.rmtree(backup)
    print('GTAVXR: Previous verified 1.0.2 installation restored; VR saves and settings untouched.', flush=True)


def recover_upgrade(args):
    if upgrade_journal(args).exists():
        print('GTAVXR: An interrupted update was found. Restoring the previous installation...', flush=True)
        check(not process_running('GTAVXR_SourceBaseline.exe'),
              'Close GTAVXR before recovering an interrupted update')
        rollback_upgrade(args)
    else:
        check(not upgrade_backup(args).exists(),
              f'Orphaned upgrade backup found: {upgrade_backup(args)}. Inspect before updating.')


def upgrade_installation(args, staged, files, previous):
    """Replace only owned files; preserve the old version until verification."""
    game = args.game.resolve()
    runtime = game.parent / '.gtavxr-linux-runtime'
    check(previous.get('release') == PREVIOUS_RELEASE and
          previous.get('runtime') == str(runtime), 'Unexpected previous installation')
    check(len(files) == UPSTREAM_PAYLOAD_COUNT + len(UPSTREAM_RUNTIME_FILES) + 3,
          'New release inventory incomplete')
    check(not process_running('GTAVXR_SourceBaseline.exe'),
          'Close GTAVXR before upgrading')
    journal_path = upgrade_journal(args)
    backup = upgrade_backup(args)
    check(not journal_path.exists() and not backup.exists(),
          'Previous upgrade journal/backup is present; recovery required')
    old = {owned_destination(game, runtime, f): f for f in previous['files']}
    new = {owned_destination(game, runtime, f): f for f in files}
    check(len(old) == len(previous['files']) and len(new) == len(files),
          'Duplicate upgrade paths detected')
    for dest, info in old.items():
        check(file_matches(dest, info),
              f'Old GTAVXR file changed; refusing upgrade: {dest}')
    for dest in new:
        check(not dest.exists() or dest in old,
              f'Unowned GTAVXR file would be overwritten: {dest}')
    # Preserve old file inodes with hardlinks where available; fall back to copies.
    backup.mkdir(mode=0o700)
    try:
        for dest, info in old.items():
            section = 'runtime' if info['kind'] in ('runtime', 'metadata') else 'game'
            saved = no_symlinks(backup, Path(section) / safe_rel(info['path']))
            saved.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(dest, saved)
            except OSError:
                shutil.copy2(dest, saved)
            check(file_matches(saved, info), f'Backup verification failed: {saved}')
        record = {'schema': 'gtavxr-linux-upgrade-v1', 'previous': previous,
                  'next_release': RELEASE, 'next_files': files}
        atomic_json(journal_path, record)
    except BaseException:
        if not journal_path.exists():
            shutil.rmtree(backup, ignore_errors=True)
        raise
    try:
        for info in files:
            dest = owned_destination(game, runtime, info)
            if file_matches(dest, info):
                continue
            source = staged / safe_rel(info['path'])
            check(file_matches(source, info), f'Staged file no longer matches manifest: {source}')
            atomic_copy_into(source, dest)
        for dest in old.keys() - new.keys():
            dest.unlink()
        state = {'schema': 'gtavxr-linux-v1', 'release': RELEASE,
                 'runtime': str(runtime), 'files': files}
        atomic_json(game / STATE_FILE, state)
        installed(args, verify=True)
    except BaseException:
        print('GTAVXR: Update failed. Attempting automatic rollback...', file=sys.stderr, flush=True)
        rollback_upgrade(args)
        raise
    journal_path.unlink()
    shutil.rmtree(backup)
    print(f'GTAVXR: Updated to 1.0.5 ({len(files)} verified files). Existing VR saves and settings preserved.', flush=True)


def atomic_json(path, obj):
    """Write state using fsync + atomic replace (never overwrite live game files)."""
    temp = path.with_name(path.name + '.tmp')
    check(not temp.exists(), f'Pending state update exists: {temp}')
    try:
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(obj, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def exclusive(action):
    """Exclude concurrent install, uninstall, and launch commands."""
    DATA_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = DATA_ROOT / 'operation.lock'
    with lock.open('a+') as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Failure('Another GTAVXR Linux operation is running')
        yield


def file_matches(path, info):
    if not path.is_file() or path.is_symlink() or path.stat().st_size != info['bytes']:
        return False
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper() == info['sha256'].upper()


def file_sha_lower(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def steam_libraries(steam):
    """Discover Steam libraries from libraryfolders.vdf, without scanning drives."""
    roots = [steam]
    vdf = steam / 'steamapps/libraryfolders.vdf'
    if vdf.is_file():
        data = vdf.read_text(encoding='utf-8', errors='replace')
        for value in re.findall(r'"path"\s*"((?:\\.|[^"\\])*)"', data):
            location = Path(value.replace('\\\\', '\\'))
            if location.is_dir():
                roots.append(location)
    unique = []
    for path in roots:
        resolved = path.expanduser().resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def discover_paths(args):
    """Prefer an explicit path, then existing v1.2 choices, then Steam libraries."""
    if args.steam is None:
        roots = (STEAM_DEFAULT, Path.home() / '.steam/steam',
                 Path.home() / '.steam/root')
        args.steam = next((p for p in roots if (p / 'steamapps').is_dir()), STEAM_DEFAULT)
    args.steam = args.steam.expanduser().resolve()
    libraries = steam_libraries(args.steam)
    if args.game is None:
        candidates = [DEFAULT_GAME]
        for root in libraries:
            apps = root / 'steamapps'
            manifest = apps / f'appmanifest_{APP_ID}.acf'
            install_dir = 'Grand Theft Auto V'
            if manifest.is_file():
                body = manifest.read_text(encoding='utf-8', errors='replace')
                match = re.search(r'"installdir"\s*"([^"\\]+)"', body)
                if match:
                    install_dir = match.group(1)
            candidates.append(apps / 'common' / install_dir)
        args.game = next((p for p in candidates if (p / 'GTA5.exe').is_file()),
                         next((p for p in candidates if p.is_dir()), DEFAULT_GAME))
    args.game = args.game.expanduser().resolve()
    # The game library might not be registered in the current libraryfolders.vdf.
    own_library = args.game.parent.parent.parent
    if (own_library / 'steamapps').is_dir() and own_library not in libraries:
        libraries.insert(0, own_library)
    if args.proton is None:
        candidates = [PROTON_DEFAULT]
        preferred_names = ('Proton 11.0', 'Proton Experimental', 'Proton Hotfix')
        for name in preferred_names:
            candidates.extend(lib / 'steamapps/common' / name / 'proton' for lib in libraries)
        for lib in libraries:
            common = lib / 'steamapps/common'
            if common.is_dir():
                candidates.extend(sorted((p / 'proton' for p in common.glob('Proton *')),
                                         key=lambda p: p.parent.name, reverse=True))
        compat = args.steam / 'compatibilitytools.d'
        if compat.is_dir():
            candidates.extend(sorted(compat.glob('*/proton'), reverse=True))
        args.proton = next((p for p in candidates if p.is_file()), PROTON_DEFAULT)
    args.proton = args.proton.expanduser().resolve()


def prompt_yes(message):
    check(sys.stdin.isatty(), f'{message} requires an interactive terminal. Use an explicit command instead.')
    return input(f'{message} [Y/n]: ').strip().lower() in ('', 'y', 'yes')


def steamvr_binary(args):
    check(args.steam.is_dir(), f'Steam installation not found: {args.steam}')
    options = [args.steam / 'steamapps/common/SteamVR/bin/linux64/vrcompositor']
    for lib in steam_libraries(args.steam):
        options.append(lib / 'steamapps/common/SteamVR/bin/linux64/vrcompositor')
    active, problem = steamvr_runtime()
    if active is not None and problem is None:
        # SteamVR OpenXR manifests live inside the SteamVR directory.
        for parent in active.parents:
            if parent.name == 'SteamVR':
                options.insert(0, parent / 'bin/linux64/vrcompositor')
                break
    binary = next((p for p in options if p.is_file()), None)
    check(binary is not None, 'SteamVR compositor not found in detected Steam libraries')
    check(not binary.is_symlink(), f'Refusing to patch a symlinked compositor: {binary}')
    return binary.resolve()


def steamvr_backup():
    return Path.home() / '.local/share/steamvr-backups/vrcompositor-v1.0'


def steamvr_running():
    if shutil.which('pgrep') is None:
        return process_running('/SteamVR/bin/linux64/vrcompositor')
    return any(subprocess.run(['pgrep', '-x', name], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, check=False).returncode == 0
               for name in ('vrcompositor', 'vrserver', 'vrmonitor'))


def atomic_binary_replace(destination, payload):
    """Write a verified executable in the same directory, then replace atomically."""
    check(destination.is_file() and not destination.is_symlink(),
          f'Not a regular executable: {destination}')
    mode = stat.S_IMODE(destination.stat().st_mode)
    fd, temp_name = tempfile.mkstemp(prefix='.vrcompositor-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, destination)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def steamvr_status(args):
    binary = steamvr_binary(args)
    checksum = file_sha_lower(binary)
    if checksum == STEAMVR_ORIGINAL_SHA:
        state = 'original'
    elif checksum == STEAMVR_PATCHED_SHA:
        state = 'patched'
    else:
        state = 'unsupported'
    return binary, checksum, state


def steamvr_maintenance(args, operation='patch'):
    binary, checksum, state = steamvr_status(args)
    if operation == 'status':
        print(f'SteamVR: {state} compositor ({checksum})')
        print(f'SteamVR compositor: {binary}')
        return state
    if operation == 'patch':
        if state == 'patched':
            print('SteamVR: Descriptor-pool fix already installed.')
            return state
        if state == 'unsupported':
            print(f'SteamVR: Unsupported or updated compositor ({checksum}); fix skipped.')
            return state
        check(not steamvr_running(),
              'SteamVR is running with the unpatched compositor. Close SteamVR completely and rerun the script.')
        original = binary.read_bytes()
        check(hashlib.sha256(original).hexdigest() == STEAMVR_ORIGINAL_SHA,
              'SteamVR compositor changed during verification')
        backup = steamvr_backup()
        check(not backup.is_symlink(), f'Refusing a symlinked backup: {backup}')
        if backup.exists():
            check(backup.is_file() and file_sha_lower(backup) == STEAMVR_ORIGINAL_SHA,
                  f'Existing SteamVR backup does not match the original compositor: {backup}')
        else:
            backup.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with backup.open('xb') as output:
                output.write(original)
                output.flush()
                os.fsync(output.fileno())
            backup.chmod(0o700)
            check(file_sha_lower(backup) == STEAMVR_ORIGINAL_SHA, 'SteamVR backup verification failed')
        data = bytearray(original)
        for offset, encoded in STEAMVR_PATCH_EDITS:
            patch = bytes.fromhex(encoded)
            data[offset:offset + len(patch)] = patch
        check(hashlib.sha256(data).hexdigest() == STEAMVR_PATCHED_SHA,
              'SteamVR patch verification failed; compositor not modified')
        check(file_sha_lower(binary) == STEAMVR_ORIGINAL_SHA,
              'SteamVR compositor changed before replacement')
        atomic_binary_replace(binary, data)
        check(file_sha_lower(binary) == STEAMVR_PATCHED_SHA,
              'SteamVR patched compositor hash mismatch')
        print('SteamVR: Descriptor-pool fix applied successfully (200 -> 10000 sets).')
        print(f'SteamVR: Original compositor backed up to {backup}')
        return 'patched'
    check(operation == 'restore', f'Unknown SteamVR operation: {operation}')
    if state == 'original':
        print('SteamVR: Original compositor already installed.')
        return state
    check(state == 'patched',
          'SteamVR compositor was updated or changed; refusing to overwrite an unknown version')
    check(not steamvr_running(), 'Close SteamVR completely before restoring its compositor')
    backup = steamvr_backup()
    check(backup.is_file() and not backup.is_symlink() and
          file_sha_lower(backup) == STEAMVR_ORIGINAL_SHA,
          'Verified original SteamVR compositor backup not found')
    check(file_sha_lower(binary) == STEAMVR_PATCHED_SHA,
          'SteamVR compositor changed before restoration')
    atomic_binary_replace(binary, backup.read_bytes())
    check(file_sha_lower(binary) == STEAMVR_ORIGINAL_SHA, 'Restored compositor verification failed')
    print('SteamVR: Original compositor restored; backup retained.')
    return 'original'


def installed(args, verify=False, allow_older=False):
    game = args.game.resolve()
    state_file = game / STATE_FILE
    check(state_file.is_file() and not state_file.is_symlink(),
          "Not installed. Run 'install' first; 'verify' only tests reconstruction.")
    state = json.loads(state_file.read_text())
    check(state.get('schema') == 'gtavxr-linux-v1' and
          state.get('release') in ({RELEASE, PREVIOUS_RELEASE} if allow_older else {RELEASE}),
          f'Unsupported or outdated installation: {state.get("release")}. Use update for 1.0.2.')
    runtime = Path(state['runtime']).resolve()
    check(runtime == game.parent / '.gtavxr-linux-runtime', 'Unexpected runtime location')
    expected_count = 1120 if state['release'] == PREVIOUS_RELEASE else (
        UPSTREAM_PAYLOAD_COUNT + len(UPSTREAM_RUNTIME_FILES) + 2 + 1)
    check(len(state['files']) == expected_count, 'Unexpected installed file count')
    check(len({(f['kind'], f['path']) for f in state['files']}) == len(state['files']),
          'Duplicate installed file path')
    for info in state['files']:
        rel = safe_rel(info['path'])
        root = runtime if info['kind'] in ('runtime', 'metadata') else game
        target = no_symlinks(root, rel)
        if verify:
            check(file_matches(target, info), f"Installed file missing or changed: {target}")
    return game, runtime, state


def wine_path(path):
    """Convert host absolute path through Proton's standard Z: drive mapping."""
    path = Path(path).resolve()
    check(path.is_absolute(), f'Not an absolute path: {path}')
    return 'Z:' + str(path).replace('/', '\\')


def vr_compat_path(args):
    path = (DATA_ROOT / 'compatdata' / APP_ID).resolve()
    # Never share the prefix with Steam's ordinary GTA V installation.
    regular = (args.game.resolve().parent.parent / 'compatdata' / APP_ID).resolve()
    check(path != regular, 'Refusing to share the regular GTA V Proton prefix')
    return path


def steamvr_runtime():
    active = Path.home() / '.config/openxr/1/active_runtime.json'
    if not active.is_file():
        return None, 'OpenXR active_runtime.json does not exist'
    try:
        d = json.loads(active.read_text())
        runtime_path = active.resolve()
        library = str(d.get('runtime', {}).get('library_path', ''))
        if 'steamvr' not in (str(runtime_path) + library).lower() and 'steamxr' not in (str(runtime_path) + library).lower():
            return runtime_path, 'Active OpenXR runtime does not appear to be SteamVR'
        return runtime_path, None
    except (OSError, ValueError):
        return None, 'Active OpenXR runtime manifest cannot be read'


def process_running(name):
    """Best-effort protection against two game instances; no signal is sent."""
    proc = Path('/proc')
    for path in proc.iterdir():
        if not path.name.isdecimal() or int(path.name) == os.getpid():
            continue
        try:
            cmd = (path / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace')
            if name.lower() in cmd.lower():
                return True
        except (OSError, PermissionError):
            continue
    return False


def verify_prefix_isolation(prefix):
    """Refuse any Wine user-data directory redirected outside the isolated pfx."""
    base = (prefix / 'pfx').resolve()
    check(base == prefix.resolve() / 'pfx', 'The isolated Proton pfx is redirected by a symbolic link')
    user = base / 'drive_c/users/steamuser'
    targets = [user, user / 'Documents', user / 'My Documents',
               user / 'AppData', user / 'AppData/Local', user / 'AppData/Roaming']
    for item in targets:
        resolved = item.resolve()
        check(resolved == base or base in resolved.parents,
              f'Unsafe Wine user-data mapping outside the isolated prefix: {item} -> {resolved}')


def prepare_vr_prefix(prefix, proton, env, game, session):
    """Create a fresh Proton prefix before starting GTA; never open normal saves."""
    prefix.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not (prefix / 'pfx/drive_c/windows').is_dir():
        init_log = session / 'prefix-initialization.log'
        print('Initializing isolated Proton prefix...', flush=True)
        with init_log.open('wb') as output:
            result = subprocess.run([str(proton), 'run', 'cmd.exe', '/c', 'exit'],
                                    env=env, cwd=game, stdout=output, stderr=subprocess.STDOUT,
                                    check=False)
        check(result.returncode == 0, f'Proton prefix initialization failed. See {init_log}')
    check((prefix / 'pfx/drive_c/windows').is_dir(), 'Proton did not initialize the isolated prefix')
    verify_prefix_isolation(prefix)


def regular_saves(args):
    """Read only the normal Proton GTA V profile saves, never the VR prefix."""
    regular = (args.game.parent.parent / 'compatdata' / APP_ID).resolve()
    vr = vr_compat_path(args)
    check(regular != vr, 'Normal GTA V and GTAVXR Proton prefixes must not overlap')
    root = regular / 'pfx/drive_c/users/steamuser/Documents/Rockstar Games/GTA V/Profiles'
    if not root.is_dir():
        return []
    results = []
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.is_symlink() or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', folder.name):
            continue
        for path in sorted(folder.iterdir()):
            if (path.is_file() and not path.is_symlink() and
                    re.fullmatch(r'SGTA5[A-Za-z0-9_.-]{0,45}', path.name, re.IGNORECASE) and
                    path.stat().st_size <= 20 * 1024 * 1024):
                results.append((folder.name, path))
    return results


def import_saves(args, prefix=None, explicit=False):
    """Copy Story Mode saves only into the isolated VR prefix; never replace a slot."""
    prefix = prefix or vr_compat_path(args)
    verify_prefix_isolation(prefix)
    sources = regular_saves(args)
    if not sources:
        if explicit:
            print('GTA V saves: No normal Proton Story Mode saves found.')
        return
    marker = DATA_ROOT / 'save-import-v1.json'
    if not explicit and marker.exists():
        return
    if not explicit:
        print(f'GTA V saves: Found {len(sources)} Story Mode save files in the normal Proton prefix.')
        if not prompt_yes('Copy normal GTA V saves into the separate GTAVXR prefix?'):
            atomic_json(marker, {'schema': 'gtavxr-linux-import-v1', 'result': 'declined'})
            print('GTA V saves: Import skipped. Original saves unchanged.')
            return
    destination_root = prefix / 'pfx/drive_c/users/steamuser/Documents/Rockstar Games/GTA V/Profiles'
    check((prefix / 'pfx/drive_c/windows').is_dir(),
          'Initialize the isolated VR Proton prefix before importing saves')
    copied = 0
    already = 0
    collisions = 0
    for profile_name, source in sources:
        dest_folder = destination_root / profile_name
        check(not dest_folder.is_symlink(), f'Unsafe destination profile symlink: {dest_folder}')
        dest_folder.mkdir(parents=True, exist_ok=True)
        destination = dest_folder / source.name
        check(not destination.is_symlink(), f'Unsafe destination save symlink: {destination}')
        check(destination.resolve().is_relative_to((prefix / 'pfx').resolve()),
              f'Destination escapes VR prefix: {destination}')
        if destination.exists():
            if destination.is_file() and file_sha_lower(destination) == file_sha_lower(source):
                already += 1
            else:
                collisions += 1
            continue
        try:
            with source.open('rb') as original, destination.open('xb') as vr_save:
                shutil.copyfileobj(original, vr_save)
            check(file_sha_lower(destination) == file_sha_lower(source),
                  f'Imported save verification failed: {destination}')
            copied += 1
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    DATA_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not marker.exists():
        atomic_json(marker, {'schema': 'gtavxr-linux-import-v1', 'result': 'copied',
                             'copied': copied, 'already': already, 'collisions': collisions,
                             'source': 'normal Proton GTA V Story Mode saves'})
    print(f'GTA V saves: Imported {copied}; already identical {already}; '
          f'existing VR slots preserved {collisions}.')
    if collisions:
        print('GTA V saves: Some slots differ from existing VR saves and were not overwritten.')


GRAPHICS_VALUES = {'ShaderQuality': 1, 'ScreenWidth': 1920, 'ScreenHeight': 1080,
                   'Windowed': 1, 'Stereo': 0}


def enforce_graphics(prefix):
    """Fix values GTA resets to unsupported defaults; preserve unrelated settings."""
    path = prefix / 'pfx/drive_c/users/steamuser/Documents/Rockstar Games/GTA V/settings.xml'
    verify_prefix_isolation(prefix)
    if not path.is_file():
        print('GTA V graphics: No settings.xml yet; launch uses -shaderQuality 1.')
        return False
    check(not path.is_symlink(), f'Refusing symlinked VR graphics settings: {path}')
    content = path.read_text(encoding='utf-8-sig')
    updated = content
    changes = []
    for name, required in GRAPHICS_VALUES.items():
        expression = re.compile(r'(<'+re.escape(name)+r'\b[^>]*?\bvalue\s*=\s*["\'])' +
                                r'(-?\d+)(["\'])', re.IGNORECASE)
        matches = list(expression.finditer(updated))
        check(len(matches) == 1, f'Expected one {name} entry in GTAVXR settings.xml; got {len(matches)}')
        old = int(matches[0].group(2))
        new = max(1, old) if name == 'ShaderQuality' else required
        if old != new:
            updated = expression.sub(lambda m: m.group(1) + str(new) + m.group(3), updated, count=1)
            changes.append(f'{name} {old}->{new}')
    if changes:
        check(path.resolve().is_relative_to((prefix / 'pfx').resolve()),
              'GTAVXR graphics settings path escapes isolated prefix')
        temp = path.with_name('settings.xml.gtavxr-tmp')
        check(not temp.exists() and not temp.is_symlink(),
              f'Temporary settings file already exists: {temp}')
        try:
            with temp.open('x', encoding='utf-8') as output:
                output.write(updated)
                output.flush()
                os.fsync(output.fileno())
            temp.chmod(stat.S_IMODE(path.stat().st_mode))
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        print('GTA V graphics: Corrected ' + ', '.join(changes))
    else:
        print('GTA V graphics: Required settings already valid.')
    return True


def check_launch(args, full_verify=True):
    game, runtime, state = installed(args, verify=full_verify)
    proton = args.proton.expanduser().resolve()
    check(proton.is_file(), f'Proton script missing: {proton}')
    steam = args.steam.expanduser().resolve()
    check(steam.is_dir(), f'Steam client installation not found: {steam}')
    check((game / 'GTA5.exe').is_file() and file_matches(game / 'GTA5.exe',
          {'sha256': BASE_SHA, 'bytes': 47467128}), 'Retail GTA5.exe changed')
    check(not process_running('GTAVXR_SourceBaseline.exe'), 'GTAVXR is already running')
    prefix = vr_compat_path(args)
    active, problem = steamvr_runtime()
    check(problem is None, f'{problem}. Set SteamVR as the active OpenXR runtime first.')
    if not args.skip_vrserver_check:
        check(shutil.which('pgrep') is not None, 'pgrep command not found')
        check(subprocess.run(['pgrep', '-x', 'vrserver'], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, check=False).returncode == 0,
              'SteamVR is not running. Start SteamVR and connect Steam Frame first.')
    return game, runtime, proton, steam, prefix, active


def status(args):
    check(not upgrade_journal(args).exists(),
          'An interrupted upgrade needs recovery. Run the launcher without arguments.')
    game, runtime, state = installed(args, verify=True, allow_older=True)
    print(f'GTAVXR release: {state["release"]}' +
          (' (upgrade available: 1.0.5)' if state['release'] == PREVIOUS_RELEASE else ''))
    print(f'PASS: {len(state["files"])} installed files match their SHA-256 hashes.')
    print(f'Game: {game}')
    print(f'Runtime: {runtime}')
    print(f'VR-only Proton prefix: {vr_compat_path(args)}')
    runtime_json, problem = steamvr_runtime()
    print(f'Native OpenXR: {runtime_json or "not found"}')
    if problem:
        print(f'OpenXR warning: {problem}')
    print(f'Proton: {args.proton} ({"present" if args.proton.is_file() else "MISSING"})')
    print('Optional mods: disabled. The VR prefix has separate saves and settings.')
    try:
        steamvr_maintenance(args, 'status')
    except Failure as error:
        print(f'SteamVR patch status unavailable: {error}')


# Experimental, opt-in OptiScaler / FSR injection. No third-party binaries are shipped.
FSR_JOURNAL = 'gtavxr-linux-fsr-stage-v1.json'


def fsr_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def fsr_pe64(path):
    """Reject obviously incorrect / 32-bit DLLs before staging."""
    with path.open('rb') as source:
        head = source.read(4096)
    if len(head) < 0x40 or head[:2] != b'MZ':
        return False
    pe = struct.unpack_from('<I', head, 0x3c)[0]
    return pe + 6 <= len(head) and head[pe:pe + 4] == b'PE\0\0' and struct.unpack_from('<H', head, pe + 4)[0] == 0x8664


def fsr_set_ini_values(original, values):
    """Change named keys under named sections without altering the source INI."""
    current = None
    done = set()
    lines = original.splitlines(keepends=True)
    result = []
    for line in lines:
        match = re.match(r'^\s*\[([^\]]+)\]', line)
        if match:
            current = match.group(1).strip().casefold()
        else:
            match = re.match(r'^(\s*)([A-Za-z][A-Za-z0-9_]*)\s*=([^\r\n]*)(\r?\n)?$', line)
            if match:
                key = (current, match.group(2).casefold())
                if key in values:
                    check(key not in done, f'Duplicate OptiScaler INI key: {key}')
                    line = match.group(1) + match.group(2) + '=' + values[key] + (match.group(4) or '')
                    done.add(key)
        result.append(line)
    check(done == set(values), f'OptiScaler configuration keys missing: {sorted(set(values) - done)}')
    return ''.join(result)


def fsr_optiscaler_config(source, mode):
    values = {
        ('upscalers', 'dx11upscaler'): 'fsr31_12' if mode == '4' else 'fsr31',
        ('upscalers', 'dx12upscaler'): 'fsr31',
        ('framegen', 'enabled'): 'false',
        ('framegen', 'fginput'): 'nofg',
        ('framegen', 'fgoutput'): 'nofg',
        ('fsr', 'fsr4update'): 'true' if mode == '4' else 'false',
    }
    return fsr_set_ini_values(source.read_text(encoding='utf-8-sig'), values).encode('utf-8')


def fsr_profile(source, destination):
    """Make a per-session SR profile. Never modify the user's normal VR profile."""
    data = source.read_text(encoding='utf-8-sig')
    match = re.search(r'(?im)^\s*\[Graphics\]\s*$', data)
    if not match:
        data += '\n[Graphics]\nupscale=quality\nneural=0\n'
    else:
        start = match.end()
        next_section = re.search(r'(?m)^\s*\[[^\]]+\]\s*$', data[start:])
        end = start + next_section.start() if next_section else len(data)
        section = data[start:end]
        for key, value in [('upscale', 'quality'), ('neural', '0')]:
            if re.search(r'(?im)^\s*' + key + r'\s*=', section):
                section = re.sub(r'(?im)^(\s*' + key + r'\s*=)[^\r\n]*', lambda m: m.group(1) + value, section, count=1)
            else:
                section += '\n' + key + '=' + value + '\n'
        data = data[:start] + section + data[end:]
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as out:
        out.write(data)
    destination.chmod(0o600)


def fsr_bridge_inputs(args, game, runtime):
    """Validate the alternate user-supplied FSR forwarder and providers."""
    check(args.optiscaler_dir is not None, 'FSR requires --optiscaler-dir /path/to/OptiScaler')
    check(args.fsr_forwarder is not None,
          'FSR requires --fsr-forwarder /path/to/nvngx.dll_gtavxr_sr.dll; see docs/linux/FSR.md')
    source = args.optiscaler_dir.expanduser().resolve()
    check(source.is_dir() and source != game and game not in source.parents,
          'OptiScaler files must be outside the GTA V directory')
    core = source / 'OptiScaler.dll'
    ini = source / 'OptiScaler.ini'
    check(core.is_file() and not core.is_symlink() and fsr_pe64(core),
          f'64-bit OptiScaler.dll not found: {core}')
    check(ini.is_file() and not ini.is_symlink(), f'OptiScaler INI not found: {ini}')
    check(core.stat().st_size <= 100 * 1024 * 1024, 'OptiScaler DLL input too large')
    configuration = fsr_optiscaler_config(ini, args.fsr)
    model_dir = args.fsr_dlss_dir.expanduser().resolve() if args.fsr_dlss_dir else source
    model = model_dir / 'nvngx_dlss.dll'
    check(model.is_file() and not model.is_symlink() and fsr_pe64(model),
          'A real x64 nvngx_dlss.dll is required. Supply --fsr-dlss-dir.')
    check(model_dir != game and game not in model_dir.parents,
          'DLSS model directory must be outside GTA V')
    alternate = args.fsr_forwarder.expanduser().resolve()
    check(alternate.is_file() and not alternate.is_symlink() and fsr_pe64(alternate),
          f'Alternate Windows x64 FSR forwarder is missing: {alternate}')
    original = runtime / 'nvngx.dll_gtavxr_sr.dll'
    check(alternate != original and fsr_sha(alternate) != fsr_sha(original),
          'FSR forwarder matches the official DLSS forwarder; build the FSR version')
    check(alternate != core and alternate != model, 'Invalid forwarder input')
    return source, core, configuration, model_dir, alternate


def fsr_stage_bridge(inputs, runtime, session):
    """Create a private session bridge, without modifying GTA or official runtime."""
    source, core, configuration, model_dir, alternate = inputs
    provider = session / 'fsr-provider'
    bridge = session / 'fsr-runtime'
    check(not provider.exists() and not provider.is_symlink() and
          not bridge.exists() and not bridge.is_symlink(),
          'Session already has FSR folders')
    provider.mkdir(mode=0o700, parents=True)
    bridge.mkdir(mode=0o700)
    shutil.copyfile(core, provider / 'OptiScaler.dll')
    # OptiScaler's NGX detection expects an nvngx.dll beside its provider.
    # The model is a user-supplied file, copied only into this VR session.
    shutil.copyfile(model_dir / 'nvngx_dlss.dll', provider / 'nvngx.dll')
    with (provider / 'OptiScaler.ini').open('xb') as output:
        output.write(configuration)
    (provider / 'OptiScaler.ini').chmod(0o600)
    for item in sorted(source.iterdir()):
        if item.name.casefold() in ('optiscaler.dll', 'optiscaler.ini', 'nvngx.dll') or item.is_symlink():
            continue
        if item.is_file() and item.suffix.casefold() == '.dll' and item.name.casefold() != 'nvngx_dlss.dll':
            (provider / item.name).symlink_to(item.resolve())
        elif item.is_dir() and item.name.casefold() in ('optiscaler', 'plugins', 'custom'):
            (provider / item.name).symlink_to(item.resolve(), target_is_directory=True)
    shutil.copyfile(runtime / 'gtavxr_native_openxr.dll', bridge / 'gtavxr_native_openxr.dll')
    shutil.copyfile(alternate, bridge / 'nvngx.dll_gtavxr_sr.dll')
    print('FSR test: Isolated NGX bridge staged; original DLSS files untouched.')



def fsr_recover(game, running=False):
    """Remove only the exact temporary files recorded by our stage journal."""
    game = game.resolve()
    journal = game / FSR_JOURNAL
    if not journal.exists() and not journal.is_symlink():
        return False
    check(not journal.is_symlink() and journal.is_file(), f'Unsafe FSR stage journal: {journal}')
    check(not running, 'An FSR-enabled GTA session may still be running. Close GTA before recovering temporary files.')
    record = json.loads(journal.read_text(encoding='utf-8'))
    check(record.get('schema') == 'gtavxr-linux-fsr-stage-v1' and record.get('game') == str(game),
          'Unknown FSR stage journal; refusing automatic cleanup')
    entries = record.get('entries')
    check(isinstance(entries, list) and len(entries) <= 100, 'Invalid FSR stage manifest')
    names = set()
    # Validate all entries before deleting any file.
    for entry in entries:
        name = entry.get('name')
        check(isinstance(name, str) and bool(re.fullmatch(r'[A-Za-z0-9_+.-]+', name)) and name != FSR_JOURNAL,
              'Unexpected FSR cleanup path')
        check(name.casefold() not in names, 'Duplicate FSR cleanup path')
        names.add(name.casefold())
        dest = game / name
        kind = entry.get('kind')
        check(kind in ('file', 'data', 'link'), 'Unknown FSR cleanup file type')
        if kind == 'link':
            if dest.exists() or dest.is_symlink():
                check(dest.is_symlink() and os.readlink(dest) == entry.get('target'),
                      f'FSR staged link changed; preserving it: {dest}')
        else:
            if dest.exists() or dest.is_symlink():
                check(dest.is_file() and not dest.is_symlink() and fsr_sha(dest) == entry.get('sha256'),
                      f'FSR staged file changed; preserving it: {dest}')
    for entry in reversed(entries):
        dest = game / entry['name']
        if dest.is_symlink() or dest.exists():
            dest.unlink()
    journal.unlink()
    print('FSR test: Temporary OptiScaler files removed.')
    return True

def launch(args):
    installed(args, verify=False)
    if not args.dry_run:
        steamvr_maintenance(args, 'patch')
    game, runtime, proton, steam, prefix, active = check_launch(args)
    # Seed from official release; keep changes between VR sessions.
    profile = DATA_ROOT / 'vr-settings.ini'
    check(file_matches(runtime / 'trial-profile/vr-settings.ini', next(
        f for f in installed(args)[2]['files'] if f['path'] == 'trial-profile/vr-settings.ini')),
        'VR settings seed is invalid')
    if not args.dry_run:
        DATA_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not profile.exists():
            shutil.copyfile(runtime / 'trial-profile/vr-settings.ini', profile)
            profile.chmod(0o600)
    session_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(os.getpid())
    session = DATA_ROOT / 'sessions' / session_id
    native = session / 'native'
    args_json = json.loads((runtime / 'suite-launch.json').read_text())
    check(args_json.get('id') == RELEASE and args_json.get('schema') == 'gtavxr-suite2-launch-v1'
          and args_json.get('session_mode') == 'suite', 'Unexpected launcher configuration')
    game_args = [wine_path(native / 'native-runtime.log') if item == '{LOGFILE}' else item
                 for item in args_json['args']]
    # Enforce ShaderQuality >= 1 on each actual launch if settings.xml exists.
    # The official launcher uses -shaderQuality 1 for a new prefix.
    user_settings = prefix / 'pfx/drive_c/users/steamuser/Documents/Rockstar Games/GTA V/settings.xml'
    if not user_settings.is_file():
        game_args.extend(['-shaderQuality', '1'])
    env = os.environ.copy()
    env.update({
        'STEAM_COMPAT_DATA_PATH': str(prefix),
        'STEAM_COMPAT_CLIENT_INSTALL_PATH': str(steam),
        'SteamAppId': APP_ID,
        'SteamGameId': APP_ID,
        'STEAM_COMPAT_APP_ID': APP_ID,
        'SteamOverlayGameId': APP_ID,
        'GTAVXR_USER_PLAY': '1',
        'GTAVXR_SESSION_DIR': wine_path(native),
        'GTAVXR_SESSIONS_ROOT': wine_path(DATA_ROOT / 'sessions'),
        'GTAVXR_VR_SETTINGS': wine_path(profile),
        'GTAVXR_BRIDGE_PATH': wine_path(runtime / 'gtavxr_native_openxr.dll'),
        'GTAVXR_LOADER_PATH': wine_path(runtime / 'openxr_loader.dll'),
        'GTAVXR_STEAMVR_BOOTSTRAP': '1',
        'GTAVXR_STEAMVR_MENU_KEY': 'F9',
        'DISABLE_XR_APILAYER_reshade_1': '1',
        'PRESSURE_VESSEL_IMPORT_OPENXR_1_RUNTIMES': '1',
    })
    if args.timing_bridge is not None:
        check(args.fsr is None, 'CPU timing bridge cannot be combined with the optional FSR bridge')
        candidate = args.timing_bridge.expanduser()
        check(candidate.is_file() and not candidate.is_symlink() and candidate.suffix.lower() == '.dll',
              f'Diagnostic bridge DLL not found or not a regular DLL: {candidate}')
        bridge = candidate.resolve()
        env['GTAVXR_BRIDGE_PATH'] = wine_path(bridge)
        env['GTAVXR_TIMING180'] = '1'
        env['GTAVXR_TIMING190'] = '1'
        env['GTAVXR_TIMING1100'] = '1'
        print(f'OpenXR CPU timing v1.10: enabled with external DLL {bridge}', flush=True)
    fsr_inputs = None
    if args.fsr:
        fsr_inputs = fsr_bridge_inputs(args, game, runtime)
        env['GTAVXR_BRIDGE_PATH'] = wine_path(session / 'fsr-runtime/gtavxr_native_openxr.dll')
        env['GTAVXR_FSR_PROVIDER_PATH'] = wine_path(session / 'fsr-provider/OptiScaler.dll')
        env['GTAVXR_DLSS_DIR'] = wine_path(fsr_inputs[3])
        if args.fsr == '4':
            env['PROTON_FSR4_UPGRADE'] = '1'
        if not args.dry_run:
            fsr_settings = session / 'vr-settings-fsr.ini'
            fsr_profile(profile, fsr_settings)
            fsr_stage_bridge(fsr_inputs, runtime, session)
            env['GTAVXR_VR_SETTINGS'] = wine_path(fsr_settings)
        print('FSR test: Separate NGX bridge requested (FSR ' + args.fsr +
              '); GPU upscaling and stereo remain unverified.')
    # Windows Khronos loader should discover Proton's wineopenxr64 through the
    # Wine registry. A Linux XR_RUNTIME_JSON would override it with an ELF runtime.
    env.pop('XR_RUNTIME_JSON', None)
    # Known workaround for GTAVXR 1.0.5 invalid PE export directory on AMD.
    dxvk = env.get('DXVK_CONFIG', '')
    if not args.no_amd_workaround:
        check('dxgi.customVendorId' not in dxvk or '8086' in dxvk,
              'DXVK_CONFIG already overrides dxgi.customVendorId. Resolve the conflict first.')
        if 'dxgi.customVendorId' not in dxvk:
            env['DXVK_CONFIG'] = (dxvk.rstrip('; ') + '; ' if dxvk.strip() else '') + 'dxgi.customVendorId = 8086'
    cmd = [str(proton), 'run', str(game / 'GTAVXR_SourceBaseline.exe'), *game_args]
    print(f'Game: {game}')
    print(f'VR Proton prefix (isolated): {prefix}')
    print(f'SteamVR host runtime: {active}')
    print(f'Proton: {proton}')
    print(('Optional isolated FSR bridge requested. ' if args.fsr else 'Optional game mods: none. ') +
          'DXVK AMD workaround: ' +
          ('disabled' if args.no_amd_workaround else 'Intel vendor ID 8086'))
    print(f'Session: {session}')
    if args.dry_run:
        import shlex
        print('DRY RUN. No Proton prefix or game session created; game not launched.')
        print('Command: ' + shlex.join(cmd))
        print('Relevant environment:')
        for key in ('STEAM_COMPAT_DATA_PATH', 'SteamGameId', 'GTAVXR_USER_PLAY',
                    'GTAVXR_SESSION_DIR', 'GTAVXR_SESSIONS_ROOT', 'GTAVXR_VR_SETTINGS',
                    'GTAVXR_BRIDGE_PATH', 'GTAVXR_TIMING180', 'GTAVXR_TIMING190', 'GTAVXR_TIMING1100', 'GTAVXR_LOADER_PATH', 'GTAVXR_STEAMVR_BOOTSTRAP',
                    'GTAVXR_FSR_PROVIDER_PATH', 'DXVK_CONFIG', 'WINEDLLOVERRIDES',
                    'GTAVXR_DLSS_DIR', 'PROTON_FSR4_UPGRADE'):
            print(f'  {key}={env.get(key, "<unset>")}')
        return
    native.mkdir(mode=0o700, parents=True, exist_ok=False)
    prepare_vr_prefix(prefix, proton, env, game, session)
    enforce_graphics(prefix)
    import_saves(args, prefix=prefix, explicit=False)
    receipt = {'schema': 'gtavxr-linux-session-v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
               'game': str(game), 'vr_prefix': str(prefix), 'runtime': str(active), 'status': 'starting'}
    atomic_json(session / 'session.json', receipt)
    print('Launching GTAVXR through Proton. The first run creates the isolated VR prefix.', flush=True)
    print(f'Output logs: {native / "stdout.log"} and {native / "stderr.log"}', flush=True)
    try:
        with (native / 'stdout.log').open('wb') as stdout, (native / 'stderr.log').open('wb') as stderr:
            child = subprocess.Popen(cmd, env=env, cwd=game, stdout=stdout, stderr=stderr)
            receipt['status'] = 'running'
            receipt['pid'] = child.pid
            atomic_json(session / 'session.json', receipt)
            rc = child.wait()
            receipt['exit_code'] = rc
            receipt['status'] = 'exited'
            receipt['ended_utc'] = datetime.now(timezone.utc).isoformat()
            atomic_json(session / 'session.json', receipt)
            print(f'GTAVXR Proton process exited with status {rc}.', flush=True)
            print(f'Logs remain in {native}', flush=True)
            if rc:
                raise Failure('GTAVXR exited with an error. Inspect stderr.log and stdout.log before changing settings.')
    except KeyboardInterrupt:
        print('Interrupted. The game process may still be running; no normal GTA saves were touched.', file=sys.stderr)
        print(f'Session log: {session}', file=sys.stderr)
        raise Failure('Launch interrupted; check for a remaining GTA process before launching again')


def uninstall(args):
    check(not process_running('GTAVXR_SourceBaseline.exe'), 'GTAVXR appears to be running; close it before uninstall')
    game = args.game.resolve()
    path = game / STATE_FILE
    check(path.is_file(), "No Linux installer state file found")
    state = json.loads(path.read_text())
    check(state.get('schema') == 'gtavxr-linux-v1' and state.get('release') in (RELEASE, PREVIOUS_RELEASE), 'Unknown installation state')
    runtime = Path(state['runtime']).resolve()
    check(runtime == game.parent / '.gtavxr-linux-runtime', 'Unexpected runtime path')
    for f in state['files']:
        root = runtime if f['kind'] in ('runtime','metadata') else game
        target = no_symlinks(root, safe_rel(f['path']))
        check(target.is_file() and digest(target.read_bytes()) == f['sha256'], f"File changed; refusing to delete: {target}")
    for f in state['files']:
        root = runtime if f['kind'] in ('runtime','metadata') else game
        (root / safe_rel(f['path'])).unlink()
    for root in (runtime, game / 'common', game / 'gtavxr_mvga147'):
        if root.exists():
            for folder in sorted((x for x in root.rglob('*') if x.is_dir()), key=lambda x:len(x.parts), reverse=True):
                if not any(folder.iterdir()): folder.rmdir()
            if not any(root.iterdir()): root.rmdir()
    path.unlink()
    print('Removed files owned by the Linux prototype; original GTA files left intact.')


def auto(args):
    print(f'GTAVXR Linux v{VERSION}')
    print(f'GTA V Legacy: {args.game} ({"found" if (args.game / "GTA5.exe").is_file() else "NOT FOUND"})')
    print(f'Proton: {args.proton} ({"found" if args.proton.is_file() else "NOT FOUND"})')
    check((args.game / 'GTA5.exe').is_file(),
          'GTA V Legacy not detected. Use --game /path/to/Grand Theft Auto V')
    check(args.proton.is_file(), 'Proton not detected. Use --proton /path/to/proton')
    if (args.game / STATE_FILE).exists():
        try:
            game, runtime, state = installed(args, verify=True, allow_older=True)
        except Failure as error:
            print(f'GTAVXR: Installation needs attention: {error}')
            # v1.5 can upgrade only a complete, verified v1.4-managed 1.0.2
            # installation. Do not try repairing it with a 1.0.5 bundle.
            prior_state = json.loads((args.game / STATE_FILE).read_text())
            if prior_state.get('release') == PREVIOUS_RELEASE:
                raise Failure('The existing 1.0.2 installation is not verified. '
                              'Repair it with the previous Linux v1.4 launcher first; '
                              'your VR prefix and saves have not been changed.') from error
            if not prompt_yes('Attempt to repair missing GTAVXR files?'):
                raise Failure('GTAVXR files were not repaired; launch cancelled')
            args.command = 'repair'
            try:
                stage(args)
            finally:
                args.command = 'auto'
            game, runtime, state = installed(args, verify=True)
        if state['release'] == PREVIOUS_RELEASE:
            print('GTAVXR: 1.0.2 installed. Official 1.0.5 is supported by this launcher.')
            check(prompt_yes('Update GTAVXR from 1.0.2 to 1.0.5?'),
                  'Update declined; the existing installation was left unchanged')
            args.command = 'update'
            try:
                stage(args)
            finally:
                args.command = 'auto'
            game, runtime, state = installed(args, verify=True)
        print(f'GTAVXR: {state["release"]} installed and verified ({len(state["files"])} files).')
    else:
        print('GTAVXR: Not installed.')
        check(prompt_yes('Install GTAVXR?'), 'GTAVXR installation declined')
        args.command = 'install'
        try:
            stage(args)
        finally:
            args.command = 'auto'
    print('GTAVXR: Starting launch checks...')
    launch(args)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', nargs='?', default='auto',
                    choices=['auto', 'verify', 'install', 'repair', 'update', 'status', 'launch',
                             'import-saves', 'steamvr-status', 'steamvr-patch',
                             'steamvr-restore', 'uninstall'])
    ap.add_argument('--game', type=Path, default=None)
    ap.add_argument('--payload', type=Path, default=None,
                    help='Use a pre-extracted local GTAVXR 1.0.5 payload ZIP')
    ap.add_argument('--installer', type=Path, default=None,
                    help='Use a local official GTAVXR 1.0.5 EXE instead of downloading it')
    ap.add_argument('--no-download', action='store_true',
                    help='Never download the official Windows GTAVXR release')
    ap.add_argument('--rpf-dir', type=Path,
                    help='Directory of pre-extracted RPF resources (otherwise rage-cli is used)')
    ap.add_argument('--rage', type=str, default=str(RAGE_DEFAULT))
    ap.add_argument('--proton', type=Path, default=None)
    ap.add_argument('--steam', type=Path, default=None)
    ap.add_argument('--timing-bridge', type=Path, default=None,
                    help='Opt-in CPU-only XR timing via a separately built Windows x64 bridge DLL')
    ap.add_argument('--dry-run', action='store_true', help='For launch only: print command, do not start game')
    ap.add_argument('--skip-vrserver-check', action='store_true',
                    help='For launch only: do not require vrserver already running')
    ap.add_argument('--fsr', choices=('3', '4'), default=None,
                    help='EXPERIMENTAL: opt-in OptiScaler FSR 3 or 4 test, not validated for GTAVXR stereo')
    ap.add_argument('--optiscaler-dir', type=Path, default=None,
                    help='Directory containing your extracted OptiScaler.dll and OptiScaler.ini')
    ap.add_argument('--fsr-dlss-dir', type=Path, default=None,
                    help='Directory containing a real x64 nvngx_dlss.dll model')
    ap.add_argument('--fsr-forwarder', type=Path, default=None,
                    help='Built Windows x64 FSR forwarder from the GitHub Actions artifact')
    ap.add_argument('--no-amd-workaround', action='store_true',
                    help='For launch only: do not apply DXVK Intel vendor spoof for AMD crash')
    args = ap.parse_args()
    args.payload_explicit = args.payload is not None
    if args.payload is None:
        args.payload = DEFAULT_PAYLOAD
    try:
        if args.fsr and args.command not in ('auto', 'launch'):
            raise Failure('--fsr is only for normal launch or explicit launch')
        if not args.fsr and (args.optiscaler_dir or args.fsr_dlss_dir or args.fsr_forwarder):
            raise Failure('Choose --fsr 3 or --fsr 4 when specifying OptiScaler inputs')
        discover_paths(args)
        if args.command in ('auto', 'install', 'repair', 'update', 'launch', 'uninstall',
                            'import-saves', 'steamvr-patch', 'steamvr-restore'):
            with exclusive(args.command):
                recover_upgrade(args)
                if args.command in ('auto', 'launch', 'install', 'repair', 'update', 'uninstall'):
                    fsr_recover(args.game, running=process_running('GTAVXR_SourceBaseline.exe'))
                if args.command == 'auto':
                    auto(args)
                elif args.command in ('install', 'repair', 'update'):
                    stage(args)
                elif args.command == 'launch':
                    launch(args)
                elif args.command == 'uninstall':
                    uninstall(args)
                elif args.command == 'import-saves':
                    installed(args, verify=False)
                    import_saves(args, explicit=True)
                elif args.command == 'steamvr-patch':
                    steamvr_maintenance(args, 'patch')
                elif args.command == 'steamvr-restore':
                    steamvr_maintenance(args, 'restore')
        elif args.command == 'status':
            status(args)
        elif args.command == 'steamvr-status':
            steamvr_maintenance(args, 'status')
        else:
            stage(args)
    except (Failure, OSError, KeyError, ValueError, StopIteration,
            zipfile.BadZipFile) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
