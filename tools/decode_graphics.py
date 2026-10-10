"""Read-only extractor for WWF Raw's mode-2 graphics compression.

Output is filled backwards in two interleaved byte lanes. The codec supports
literal blocks, constant runs, descending-value runs and backreferences.
A complete game emulator comparison remains outstanding.
"""

from pathlib import Path
import argparse
import collections
import hashlib
import json


class DecodeError(ValueError):
    pass


def decode_mode2(rom, offset):
    if offset < 0 or offset + 3 > len(rom):
        raise DecodeError("Header outside ROM")
    length = int.from_bytes(rom[offset : offset + 2], "little")
    if rom[offset + 2] != 2:
        raise DecodeError("Only mode 2 is implemented")
    if length == 0:
        raise DecodeError("Zero length not supported")
    end = offset + 3
    p = end
    output = bytearray(length)
    written = set()
    commands = collections.Counter()
    # The machine's first pass fills odd addresses; its second fills even.
    y = length + (1 if length % 2 == 0 else 0)
    first = True

    def read():
        nonlocal p
        if p >= len(rom):
            raise DecodeError("Truncated compressed input")
        if (p >> 16) != (offset >> 16):
            raise DecodeError("Input crosses bank boundary; not supported")
        v = rom[p]
        p += 1
        return v

    def put(address, value):
        if not 0 <= address < length:
            raise DecodeError(f"Output address {address} out of bounds")
        if address in written:
            raise DecodeError(f"Output address {address} overwritten")
        output[address] = value
        written.add(address)

    for _ in range(length * 2 + 1024):
        if first and y == 1:
            y = length + (length & 1)
            first = False
        control = read()
        if control & 0x80:
            distance = (((control & 7) << 8) | read()) + 1
            count = ((control & 0x78) >> 3) + 3
            y -= 2 * count
            source = y + 2 * distance
            if source >= length:
                source = source - length + (1 if length % 2 == 0 else 0)
            for i in reversed(range(count)):
                s = source + 2 * i
                if s not in written:
                    raise DecodeError(f"Backreference to uninitialized output {s}")
                put(y + 2 * i, output[s])
            commands["backreference"] += 1
        elif control & 0x40:
            count = (control & 0x3F) + 1
            values = [read() for _ in range(count)]
            y -= 2 * count
            for i, v in enumerate(values):
                put(y + 2 * i, v)
            commands["literal"] += 1
        elif not control & 0x20:
            if control == 0:
                if len(written) != length:
                    raise DecodeError(
                        f"Incomplete output: {len(written)} of {length} bytes"
                    )
                return bytes(output), {
                    "offset": f"0x{offset:06X}",
                    "mode": 2,
                    "decoded_size": length,
                    "compressed_size": p - offset,
                    "commands": dict(commands),
                    "sha256": hashlib.sha256(output).hexdigest(),
                }
            count = (control & 31) + 2
            value = read()
            y -= 2 * count
            for i in range(count):
                put(y + 2 * i, value)
            commands["constant_run"] += 1
        else:
            count = (control & 31) + 3
            value = read()
            for i in range(count):
                y -= 2
                put(y, (value - i) & 255)
            commands["descending_run"] += 1
    raise DecodeError("Command limit exceeded")


def decode_mode1(rom, offset):
    """Decode the contiguous-byte path; mode-2 uses two interleaved lanes."""
    if offset < 0 or offset + 3 > len(rom):
        raise DecodeError("Header outside ROM")
    length = int.from_bytes(rom[offset : offset + 2], "little")
    if rom[offset + 2] != 1 or length == 0:
        raise DecodeError("Expected nonzero mode-1 block")
    output = bytearray(length)
    written = set()
    commands = collections.Counter()
    p = offset + 3
    y = length

    def read():
        nonlocal p
        if p >= len(rom) or p >> 16 != offset >> 16:
            raise DecodeError("Input truncated or crosses a bank boundary")
        value = rom[p]
        p += 1
        return value

    def put(address, value):
        if not 0 <= address < length or address in written:
            raise DecodeError("Output out of bounds or overwritten")
        output[address] = value
        written.add(address)

    def copy(count, distance):
        nonlocal y
        y -= count
        for i in reversed(range(count)):
            source = y + i + distance
            if source not in written:
                raise DecodeError("Backreference to uninitialized output")
            put(y + i, output[source])

    for _ in range(length * 2 + 1024):
        control = read()
        if control & 0x80:
            distance = (((control & 7) << 8) | read()) + 1
            copy(((control & 0x78) >> 3) + 3, distance)
            commands["backreference"] += 1
        elif control & 0x40:
            count = (control & 63) + 1
            values = [read() for _ in range(count)]
            y -= count
            for i, value in enumerate(values):
                put(y + i, value)
            commands["literal"] += 1
        elif control & 0x20:
            copy(1, (control & 31) + 1)
            commands["single_backreference"] += 1
        elif control:
            count = (control & 31) + 2
            value = read()
            y -= count
            for i in range(count):
                put(y + i, value)
            commands["constant_run"] += 1
        else:
            if len(written) != length:
                raise DecodeError("Incomplete output")
            return bytes(output), {
                "offset": f"0x{offset:06X}",
                "mode": 1,
                "decoded_size": length,
                "compressed_size": p - offset,
                "commands": dict(commands),
                "sha256": hashlib.sha256(output).hexdigest(),
            }
    raise DecodeError("Command limit exceeded")


def decode_block(rom, offset):
    if offset < 0 or offset + 3 > len(rom):
        raise DecodeError("Header outside ROM")
    mode = rom[offset + 2]
    if mode == 1:
        return decode_mode1(rom, offset)
    if mode == 2:
        return decode_mode2(rom, offset)
    raise DecodeError(f"Unsupported compression mode {mode}")


def render(data, path):
    from PIL import Image
    from inspect_rom import tile

    count = len(data) // 32
    width = 128
    height = max(8, ((count + 15) // 16) * 8)
    image = Image.new("RGB", (width, height), "#202020")
    for t in range(count):
        for k, v in enumerate(tile(data, t * 32, 4)):
            shade = v * 17
            image.putpixel(
                (t % 16 * 8 + k % 8, t // 16 * 8 + k // 8), (shade, shade, shade)
            )
    image.resize((width * 4, height * 4), Image.Resampling.NEAREST).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument(
        "--offset", type=lambda x: int(x, 0), action="append", required=True
    )
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--verify-reference", action="store_true")
    args = ap.parse_args()
    rom = args.rom.read_bytes()
    if len(rom) % 1024 == 512:
        rom = rom[512:]
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for off in args.offset:
        data, result = decode_block(rom, off)
        if args.verify_reference:
            from decoder_reference import reference_decode

            reference, cpu = reference_decode(rom, off)
            if data != reference:
                raise DecodeError(f"Reference mismatch at {off:06X}")
            result["reference_match"] = True
            result["reference_instructions"] = cpu.steps
        (args.output / f"{off:06x}.bin").write_bytes(data)
        render(data, args.output / f"{off:06x}-4bpp.png")
        results.append(result)
    (args.output / "extraction.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
