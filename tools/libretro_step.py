"""Frame-stepping libretro harness for building controller recipes (same core setup as tools/run_headless.py).

The caller decides each frame's held buttons; memory is only read. Nothing is written to emulator memory.

    emu = Emulator(core_path, rom_path)
    emu.step({0: {7}, 1: set()})   # hold Right on port 0 for one frame
    wram = emu.wram()
"""
import ctypes as ct
from pathlib import Path

from run_headless import GameInfo, ENV, VIDEO, AUDIO, BATCH, POLL, INPUT


class Emulator:
    def __init__(self, core, rom, state=None, directory='/tmp'):
        self.core = ct.CDLL(str(Path(core).resolve()))
        self.held = {0: set(), 1: set()}
        self.frame = 0
        self.last_video = None
        self._directory = str(directory).encode()
        self._pixel_format = 0
        core_ = self.core

        @ENV
        def environment(command, data):
            if command in (9, 31):
                ct.cast(data, ct.POINTER(ct.c_char_p))[0] = self._directory
                return True
            if command == 10:
                self._pixel_format = ct.cast(data, ct.POINTER(ct.c_uint))[0]
                return self._pixel_format in (0, 1, 2)
            if command == 3:
                ct.cast(data, ct.POINTER(ct.c_bool))[0] = True
                return True
            if command == 15:
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
            if data and data != ct.c_void_p(-1).value:
                self.last_video = (ct.string_at(data, pitch * height), width, height, pitch, self._pixel_format)

        @AUDIO
        def audio(left, right):
            pass

        @BATCH
        def batch(data, count):
            return count

        @POLL
        def poll():
            pass

        @INPUT
        def input_state(port, device, index, button):
            return int(device == 1 and button in self.held.get(port, ()))

        self._callbacks = (environment, video, audio, batch, poll, input_state)
        for name, typ, cb in [('environment', ENV, environment), ('video_refresh', VIDEO, video),
                              ('audio_sample', AUDIO, audio), ('audio_sample_batch', BATCH, batch),
                              ('input_poll', POLL, poll), ('input_state', INPUT, input_state)]:
            fn = getattr(core_, 'retro_set_' + name)
            fn.argtypes = [typ]
            fn.restype = None
            fn(cb)
        core_.retro_init.restype = None
        core_.retro_init()
        core_.retro_load_game.argtypes = [ct.POINTER(GameInfo)]
        core_.retro_load_game.restype = ct.c_bool
        data = Path(rom).read_bytes()
        self._rom = ct.create_string_buffer(data)
        info = GameInfo(str(Path(rom).resolve()).encode(), ct.cast(self._rom, ct.c_void_p), len(data), None)
        if not core_.retro_load_game(ct.byref(info)):
            raise RuntimeError('Core rejected ROM')
        core_.retro_set_controller_port_device.argtypes = [ct.c_uint, ct.c_uint]
        core_.retro_set_controller_port_device(0, 1)
        core_.retro_set_controller_port_device(1, 1)
        core_.retro_get_memory_data.argtypes = [ct.c_uint]
        core_.retro_get_memory_data.restype = ct.c_void_p
        core_.retro_get_memory_size.argtypes = [ct.c_uint]
        core_.retro_get_memory_size.restype = ct.c_size_t
        core_.retro_serialize_size.restype = ct.c_size_t
        core_.retro_serialize.argtypes = [ct.c_void_p, ct.c_size_t]
        core_.retro_serialize.restype = ct.c_bool
        core_.retro_unserialize.argtypes = [ct.c_void_p, ct.c_size_t]
        core_.retro_unserialize.restype = ct.c_bool
        core_.retro_run.restype = None
        if state:
            self.load_state(Path(state).read_bytes())

    def step(self, held=None):
        if held is not None:
            self.held = {p: set(b) for p, b in held.items()}
        self.core.retro_run()
        self.frame += 1

    def wram(self):
        size = self.core.retro_get_memory_size(2)
        return ct.string_at(self.core.retro_get_memory_data(2), size)

    def save_state(self):
        size = self.core.retro_serialize_size()
        buf = ct.create_string_buffer(size)
        if not self.core.retro_serialize(buf, size):
            raise RuntimeError('serialize failed')
        return buf.raw

    def load_state(self, data):
        buf = ct.create_string_buffer(data)
        if not self.core.retro_unserialize(buf, len(data)):
            raise RuntimeError('unserialize failed')
