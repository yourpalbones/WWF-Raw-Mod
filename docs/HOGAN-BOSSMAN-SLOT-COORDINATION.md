# Added-slot work while Claude owns artwork and editor coverage

User authorization: add Boss Man and get Hogan onto the roster, provided this does not interfere with Claude.

Codex keeps this work on `codex/hogan-bossman-slots`. Claude PR #1 and its editor, importer, receiver builders and coverage files are unchanged. Current native test base is PR head `7b06f6e`. New work is confined to Codex's Hogan/Boss Man tools and evidence.

Native prototype: logical slots 13 and 14, selectors 26 and 28, 15 total. Player-role guards distinguish the referee/NPC selectors. Hooks wrap the existing thirteen-slot dispatchers and leave their code present. The first 13 profile records and populated gear bytes are preserved in the tested export.

Blocking integration issue: banks 4A/54/55 and 5D/5E/6D are unused in this immutable export but reserved by the gear builders. Do not merge this allocator or use the current editor to save the prototype. Agree on permanent storage or coordinated gear reservations before browser integration. Editor slot recognition, profile/HUD expansion, exports, previews and future complete-animation ownership also need coordination. Boss Man's finisher is not imported and all ordinary/receiving/recovery gaps remain open.

Independent Codex fix: Hogan's compressed HUD atlas is 8,324 bytes; the former 8,192-byte protection allowed its tail to be overwritten by tile packets. Its protected gap is now 12 KiB, with a decoder/bounds guard. This was unrelated to Claude's work.

Evidence: `evidence/hogan-bossman-15-slots/README.md`.
