"""Private paired-animation build: receiving drawings for every slot with a receiving art source.

The install itself is editor/perfect-receiver-core.js (one implementation, run here through Node by
tools/receivers_cli.js), so Python and browser output are identical by construction. This module generates
the ROM hooks and the storage layout that the manifest (tools/build_perfect_receiver_manifest.py) bundles.
"""
import argparse,json,subprocess
from pathlib import Path
from build_nwo_gear import emit_address
from build_shawn_kick_prototype import Program

ROOT=Path(__file__).resolve().parents[1]
ORIGIN_X=72   # receiver canvas origin (data/perfect-receivers.json "canonical")
DESCRIPTOR_BANK=0x71
# RX3 storage: only the Perfect import and these drawings use these ranges (all verified free in fresh, v0.16
# and gear-modded imports). 7E8000-7EFFFF and 7F8000-7FFFFF are reached as $3E:8000 / $3F:8000.
LAYOUT={'marker':'ROYAL-RX3','tables':[0x71d000,0x720000],'descriptors':[0x711900,0x716800],
        'pointer_table':0x7da000,'pointer_end':0x7de000,
        'pools':[[0x700000,0x708000],[0x7e8000,0x7f0000],[0x7f8000,0x800000],[0x716800,0x71d000],[0x7de000,0x7e0000]]}
# Receiving art source per Raw slot.
# - 'royal': Royal Rumble's drawings of the same person (Bret, Undertaker, Yokozuna, Razor, Lex, Shawn, Perfect).
#   'stock_identity_only' skips it when a gear identity replaces the character (Scott Hall over Razor) and
#   uses 'fallback' instead.
# - 'reskin': Royal's receiving drawing of the closest-built donor, pixel for pixel in shape and placement, with
#   every pixel copied from the wrestler's own art at the matching place on their body (tools/plan_receiver_reskin.py,
#   data/receiver-reskin-plan.json); a gear identity has its own plan. For workers with no Royal counterpart of the
#   same identity.
# - 'own_profiles' (superseded after review, kept for comparison): the wrestler's own Raw poses chosen to follow
#   Royal's Perfect-Plex step by step
#   (tools/plan_receiver_profiles.py, data/receiver-profile-plan.json), drawn from the user's ROM, with Royal's
#   anchors; a gear identity has its own plan. For workers with no Royal counterpart of the same identity.
# - 'own_native' (superseded, kept for comparison): Raw's own receiving-suplex sequence re-timed. Its drawings
#   lifted and dropped the receiver beside Mr. Perfect instead of over him.
OWN_NATIVE_STEPS=[[0,0,0],[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,0,0],[3,0,0],[6,0,8],[10,0,0]]
SLOTS={0:{'source':'reskin'},1:{'source':'royal','selector':3},2:{'source':'royal','selector':2},
       3:{'source':'royal','selector':9},4:{'source':'reskin'},
       5:{'source':'royal','selector':8,'stock_identity_only':True,'fallback':'reskin'},
       6:{'source':'royal','selector':10},7:{'source':'reskin'},8:{'source':'royal','selector':7},
       9:{'source':'reskin'},10:{'source':'reskin'},11:{'source':'reskin'},
       12:{'source':'royal','selector':1}}


def worker_hook():
    p=Program();p.emit('08 48 da 5a a6 36 bd ec 0b c9 51 50');p.branch('f0','receiver')
    p.emit('c9 52 50');p.branch('d0','original')
    p.label('receiver');p.emit('bd 74 0b c9 1a 00');p.branch('b0','original')
    # slot*3 from the selector word without touching direct page: $90 is the stock part loader's
    # running object total (80:EC97 STZ, 80:ECE4 ADC); writing it caused extra stale objects (PP-7).
    p.emit('48 4a 18 63 01 aa 68');emit_address(p,'bf',0x71d000);p.branch('f0','original')
    p.emit('85 84 a9 71 00 85 86 a3 05 c9 10 0e');p.branch('90','original')
    p.emit('c9 34 0e');p.branch('b0','original')
    p.emit('38 e9 10 0e a8 b7 84 85 80 c8 c8 b7 84 29 ff 00 85 82')
    p.emit('7a fa 68 28 a5 80 99 4e 05 a5 82 99 50 05 c8 c8 5c e2 ec 80')
    p.label('original');p.emit('7a fa 68 28');emit_address(p,'5c',0x71e800)
    return p.finish()


def lookup_hook():
    p=Program();p.emit(f'48 a5 82 29 ff 00 c9 {DESCRIPTOR_BANK:02x} 00');p.branch('d0','original')
    p.emit('68 c9 00 c0');p.branch('90','stock')
    p.emit('29 ff 3f da 48 0a 18 63 01 aa 68')
    emit_address(p,'bf',LAYOUT['pointer_table']);p.emit('85 db e2 20');emit_address(p,'bf',LAYOUT['pointer_table']+2)
    p.emit('85 dd c2 20 fa a9 01 00 6b')
    p.label('original');p.emit('68')
    p.label('stock');emit_address(p,'5c',0x71e900)
    return p.finish()


def sequence_hook():
    p=Program();p.emit('08 48 da a6 36 bd ec 0b c9 51 50');p.branch('f0','receiver')
    p.emit('c9 52 50');p.branch('d0','original')
    # A on entry is the action being dispatched; test it rather than 06B4,X (see PP-4).
    p.label('receiver');p.emit('a3 03 c9 1c 02');p.branch('d0','leaving')
    p.emit('bd 74 0b c9 1a 00');p.branch('b0','original')
    p.emit('48 4a 18 63 01 aa 68');emit_address(p,'bf',0x71d040);p.branch('f0','original')
    # Keep the stream base in $7C: the hooked instruction (80:F073 STA $7C) overwrites it anyway.
    p.emit('85 7c a6 36 a5 48 c9 3f 00');p.branch('90','ready')
    p.emit('bd ec 0b c9 51 50');p.branch('d0','ready')
    p.emit('a9 01 00 9d d8 0a a9 52 50 9d ec 0b')
    p.label('ready');p.emit('fa 68 28 a9 71 00 85 7e a5 48 18 65 7c 85 7c 5c 80 f0 80')
    # Leaving the receiving stream (receiver state, next action dispatched): the stock sequence tables
    # are in bank C4. The chained hook only restores the bank from 73 (attacker stream), so restore it
    # from this stream's bank 71 here; otherwise action 70 reads its first step from bank 71 and never
    # requests a frame (PP-4). Other actors keep the original, unchanged path and timing.
    p.label('leaving');p.emit('a5 7e c9 71 00');p.branch('d0','original');p.emit('a9 c4 00 85 7e')
    p.label('original');p.emit('fa 68 28');emit_address(p,'5c',0x71ea00)
    return p.finish()


def build(base_path,royal_path,output):
    """Install through the browser core (tools/receivers_cli.js); returns its report."""
    result=subprocess.run(['node',str(ROOT/'tools/receivers_cli.js'),'install',str(base_path),str(royal_path),str(output)],
                          check=True,capture_output=True,text=True)
    return json.loads(result.stdout)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('royal',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    report=build(args.raw,args.royal,args.output)
    args.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
