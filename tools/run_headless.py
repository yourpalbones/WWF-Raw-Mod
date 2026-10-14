"""Run a supplied Snes9x libretro core locally; capture video and PPU memory.

The optional research patch adds read-only decoder/DMA tracing and exposes
CGRAM, OAM and the register mirror as custom memory IDs. No GUI is required.
"""

import argparse
import ctypes as ct
import json
from pathlib import Path
import os
import wave
import struct
from PIL import Image


class GameInfo(ct.Structure):
    _fields_ = [
        ("path", ct.c_char_p),
        ("data", ct.c_void_p),
        ("size", ct.c_size_t),
        ("meta", ct.c_char_p),
    ]


class Variable(ct.Structure):
    _fields_ = [("key", ct.c_char_p), ("value", ct.c_char_p)]


class Geometry(ct.Structure):
    _fields_ = [("base_width", ct.c_uint), ("base_height", ct.c_uint),
                ("max_width", ct.c_uint), ("max_height", ct.c_uint),
                ("aspect_ratio", ct.c_float)]


class Timing(ct.Structure):
    _fields_ = [("fps", ct.c_double), ("sample_rate", ct.c_double)]


class AVInfo(ct.Structure):
    _fields_ = [("geometry", Geometry), ("timing", Timing)]


ENV = ct.CFUNCTYPE(ct.c_bool, ct.c_uint, ct.c_void_p)
VIDEO = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_uint, ct.c_uint, ct.c_size_t)
AUDIO = ct.CFUNCTYPE(None, ct.c_int16, ct.c_int16)
BATCH = ct.CFUNCTYPE(ct.c_size_t, ct.c_void_p, ct.c_size_t)
POLL = ct.CFUNCTYPE(None)
INPUT = ct.CFUNCTYPE(ct.c_int16, ct.c_uint, ct.c_uint, ct.c_uint, ct.c_uint)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("core", type=Path)
    ap.add_argument("rom", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--frames", type=int, default=1800)
    ap.add_argument("--interval", type=int, default=120)
    ap.add_argument("--snapshot-frame",type=int,action="append",default=[],help="Capture an additional specific frame without increasing periodic snapshot frequency")
    ap.add_argument(
        "--press",
        action="append",
        default=[],
        help="frame:button_id[:duration]; START=3, A=8, B=0, directions=4..7",
    )
    ap.add_argument("--load-state", type=Path)
    ap.add_argument("--images-only", action="store_true", help="Capture PNG frames without memory dumps or save states")
    ap.add_argument("--controller-device", type=int, help="Explicit libretro controller device for both ports (Genesis capture)")
    ap.add_argument("--audio", action="store_true", help="Capture local stereo PCM audio for sound research")
    ap.add_argument(
        "--press-p2",
        action="append",
        default=[],
        help="Player 2 frame:button_id[:duration], using the same IDs as --press",
    )
    args = ap.parse_args()
    if args.frames < 1 or args.interval < 1:
        raise ValueError("Frame count and snapshot interval must be positive")
    if any(n<1 or n>args.frames for n in args.snapshot_frame):
        raise ValueError("Specific snapshot frames must be within the run")
    extra_snapshots=set(args.snapshot_frame)
    args.output.mkdir(parents=True, exist_ok=True)
    if any(path.is_file() for path in args.output.rglob("*")):
        raise ValueError("Choose an empty output directory for each run")
    trace = os.environ.get("WWF_TRACE_DIR")
    if trace:
        if Path(trace).resolve() != args.output.resolve():
            raise ValueError("WWF_TRACE_DIR must match the output directory")
        (args.output / "assets").mkdir(exist_ok=True)
    directory = str(args.output.resolve()).encode()
    core = ct.CDLL(str(args.core.resolve()))
    frame = 0
    pixel_format = 0
    last_frame = None
    audio_frames = bytearray()
    presses = []
    for port, schedule in enumerate((args.press, args.press_p2)):
        for p in schedule:
            parts = list(map(int, p.split(":")))
            if len(parts) not in (2, 3):
                raise ValueError("Press must be frame:button_id[:duration]")
            start, button = parts[:2]
            duration = parts[2] if len(parts) == 3 else 8
            if start < 1 or button not in range(16) or duration < 1:
                raise ValueError("Invalid press frame, button or duration")
            presses.append((port, start, button, duration))

    @ENV
    def environment(command, data):
        nonlocal pixel_format
        if command in (9, 31):
            ct.cast(data, ct.POINTER(ct.c_char_p))[0] = directory
            return True
        if command == 10:
            pixel_format = ct.cast(data, ct.POINTER(ct.c_uint))[0]
            return pixel_format in (0, 1, 2)
        if command == 3:
            ct.cast(data, ct.POINTER(ct.c_bool))[0] = True
            return True
        if command == 15:
            ct.cast(data, ct.POINTER(Variable)).contents.value = None
            return False
        if command in (17, 49):
            ct.cast(data, ct.POINTER(ct.c_bool))[0] = False
            return True
        if command in (39, 52):
            ct.cast(data, ct.POINTER(ct.c_uint))[0] = 0
            return True
        if command == (47 | 0x10000):
            ct.cast(data, ct.POINTER(ct.c_int))[0] = 3
            return True
        return command in (16, 18, 35, 36, 53)

    @VIDEO
    def video(data, width, height, pitch):
        nonlocal last_frame
        if data and data != ct.c_void_p(-1).value:
            last_frame = (
                ct.string_at(data, pitch * height),
                width,
                height,
                pitch,
                pixel_format,
            )

    @AUDIO
    def audio(left, right):
        if args.audio:audio_frames.extend(struct.pack("<hh",left,right))

    @BATCH
    def batch(data, count):
        if args.audio:audio_frames.extend(ct.string_at(data,count*4))
        return count

    @POLL
    def poll():
        pass

    @INPUT
    def input_state(port, device, index, button):
        if port not in (0, 1) or device != 1:
            return 0
        return int(
            any(
                start <= frame < start + duration and b == button and p == port
                for p, start, b, duration in presses
            )
        )

    for name, typ, callback in [
        ("environment", ENV, environment),
        ("video_refresh", VIDEO, video),
        ("audio_sample", AUDIO, audio),
        ("audio_sample_batch", BATCH, batch),
        ("input_poll", POLL, poll),
        ("input_state", INPUT, input_state),
    ]:
        function = getattr(core, "retro_set_" + name)
        function.argtypes = [typ]
        function.restype = None
        function(callback)
    core.retro_init.restype = None
    core.retro_init()
    core.retro_load_game.argtypes = [ct.POINTER(GameInfo)]
    core.retro_load_game.restype = ct.c_bool
    rom = args.rom.read_bytes()
    buffer = ct.create_string_buffer(rom)
    info = GameInfo(
        str(args.rom.resolve()).encode(), ct.cast(buffer, ct.c_void_p), len(rom), None
    )
    if not core.retro_load_game(ct.byref(info)):
        raise RuntimeError("Core rejected ROM")
    core.retro_set_controller_port_device.argtypes = [ct.c_uint, ct.c_uint]
    core.retro_set_controller_port_device(0, 1)
    core.retro_set_controller_port_device(1, 1)
    core.retro_get_memory_data.argtypes = [ct.c_uint]
    core.retro_get_memory_data.restype = ct.c_void_p
    core.retro_get_memory_size.argtypes = [ct.c_uint]
    core.retro_get_memory_size.restype = ct.c_size_t
    core.retro_serialize_size.restype = ct.c_size_t
    core.retro_serialize.argtypes = [ct.c_void_p, ct.c_size_t]
    core.retro_serialize.restype = ct.c_bool
    core.retro_unserialize.argtypes = [ct.c_void_p, ct.c_size_t]
    core.retro_unserialize.restype = ct.c_bool
    if args.load_state:
        state = args.load_state.read_bytes()
        sb = ct.create_string_buffer(state)
        if not core.retro_unserialize(sb, len(state)):
            raise RuntimeError("Core rejected save state")

    if args.controller_device is not None:
        core.retro_set_controller_port_device.argtypes = [ct.c_uint, ct.c_uint]
        for port in (0, 1):
            core.retro_set_controller_port_device(port, args.controller_device)

    def snapshot():
        prefix = args.output / f"frame-{frame:06d}"
        if last_frame:
            raw, width, height, pitch, fmt = last_frame
            rgb = bytearray(width * height * 3)
            bytes_per_pixel = 4 if fmt == 1 else 2
            for y in range(height):
                for x in range(width):
                    pos = y * pitch + x * bytes_per_pixel
                    value = int.from_bytes(raw[pos : pos + bytes_per_pixel], "little")
                    if fmt == 1:
                        color = ((value >> 16) & 255, (value >> 8) & 255, value & 255)
                    else:
                        r = (value >> (11 if fmt == 2 else 10)) & 31
                        g = (value >> 5) & (63 if fmt == 2 else 31)
                        b = value & 31
                        color = (
                            r * 255 // 31,
                            g * 255 // (63 if fmt == 2 else 31),
                            b * 255 // 31,
                        )
                    i = (y * width + x) * 3
                    rgb[i : i + 3] = bytes(color)
            Image.frombytes("RGB", (width, height), bytes(rgb)).save(
                str(prefix) + ".png"
            )
        if args.images_only:
            return
        for ident, name in [
            (2, "wram"),
            (3, "vram"),
            (0x10010, "cgram"),
            (0x10011, "oam"),
            (0x10012, "registers"),
            (0x10013, "spc-ram"),
            (0x10014, "dsp-registers"),
        ]:
            ptr = core.retro_get_memory_data(ident)
            size = core.retro_get_memory_size(ident)
            if ptr and size:
                Path(str(prefix) + "-" + name + ".bin").write_bytes(
                    ct.string_at(ptr, size)
                )
        size = core.retro_serialize_size()
        sb = ct.create_string_buffer(size)
        if not core.retro_serialize(sb, size):
            raise RuntimeError("Save-state capture failed")
        Path(str(prefix) + ".state").write_bytes(sb.raw)

    audio_rate = 0
    if args.audio:
        av = AVInfo()
        core.retro_get_system_av_info.argtypes = [ct.POINTER(AVInfo)]
        core.retro_get_system_av_info(ct.byref(av))
        audio_rate = round(av.timing.sample_rate)
        if audio_rate <= 0:raise RuntimeError("Core did not supply an audio sample rate")
    core.retro_run.restype = None
    for frame in range(1, args.frames + 1):
        core.retro_run()
        if frame % args.interval == 0 or frame == args.frames or frame in extra_snapshots:
            snapshot()
            print(f"Captured frame {frame}", flush=True)
    (args.output / "run.json").write_text(
        json.dumps(
            {
                "core": str(args.core.resolve()),
                "frames": args.frames,
                "interval": args.interval,
                "snapshot_frames": sorted(extra_snapshots),
                "presses": presses,
                "loaded_state": str(args.load_state) if args.load_state else None,
            },
            indent=2,
        )
        + "\n"
    )
    if args.audio:
        with wave.open(str(args.output / "audio.wav"), "wb") as audio_file:
            audio_file.setnchannels(2);audio_file.setsampwidth(2);audio_file.setframerate(audio_rate);audio_file.writeframes(audio_frames)
    core.retro_unload_game()
    core.retro_deinit()


if __name__ == "__main__":
    main()
