extends Object

# Bestiary population — spawns hostile NPCs (npc.gd) across the three worlds.
# Bipeds use the Unity-baked _anim.fbx rig with the KD6 walk clip merged in;
# quadrupeds use the multi-clip _v2.glb. Each NPC is a CharacterBody3D that
# wanders near its home spot until the player comes within aggro range, then
# chases and attacks. Creatures with baked _swipe/_die clips play them; the
# rest fall back to a clip-less lunge + fade-out death (see npc.gd).
# Heights are miniature-world targets (kit walls are 1.3m).

const NpcScript := preload("res://scripts/npc.gd")

# Per-world wander half-extents (all three worlds are origin-centered). Kept
# inside the walls and clear of the biggest building footprints.
const ARENA := {
	"courtyard": Vector2(6.0, 6.0),
	"interior": Vector2(3.2, 4.5),
	"town": Vector2(6.0, 8.0),
}

# The 13-creature roster now lives as EnemyDef resources under data/enemies/
# (one .tres per creature), split 5/5/3 so each world is a distinct fight. A new
# enemy is a new data file, not a code edit. Stats/kind/home/world all come from
# the resource; per-world wander bounds stay in ARENA above.
const ENEMY_DIR := "res://data/enemies"

static func build(world := "courtyard") -> Node3D:
	var root := Node3D.new()
	root.name = "Bestiary"
	var arena: Vector2 = ARENA.get(world, Vector2(6.0, 6.0))
	for def in _load_defs():
		if def.world != world:
			continue
		_spawn_npc(root, def, arena)
	return root

# Load every EnemyDef under data/enemies/, sorted by id for deterministic spawn
# order across verification runs.
static func _load_defs() -> Array:
	var defs: Array = []
	var dir := DirAccess.open(ENEMY_DIR)
	if dir == null:
		push_warning("bestiary: cannot open %s" % ENEMY_DIR)
		return defs
	var names := dir.get_files()
	names.sort()
	for f in names:
		if not f.ends_with(".tres"):
			continue
		var def: Resource = load("%s/%s" % [ENEMY_DIR, f])
		if def != null:
			defs.append(def)
	return defs

static func _spawn_npc(parent: Node3D, def: Resource, arena: Vector2) -> void:
	var npc := CharacterBody3D.new()
	npc.name = def.id
	npc.set_script(NpcScript)
	npc.cfg = {
		"name": def.id, "kind": def.kind, "target_h": def.target_h,
		"home": def.home, "arena": arena,
		"hp": def.hp, "dmg": def.dmg, "hostile": def.hostile,
		"ranged": def.ranged,
	}
	npc.position = Vector3(def.home.x, 0.1, def.home.y)  # floor tile tops sit at ~0.1
	parent.add_child(npc)
