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

# world -> [name, kind, target_h (m), home (x, z)]. The 13-creature roster is
# split 5/5/3 so each world is a distinct fight.
const POP := {
	"courtyard": [
		["skeleton_warrior", "biped", 0.80, Vector2(0.7, 3.0)],
		["ghoul", "biped", 0.75, Vector2(-4.0, 1.5)],
		["plague_zombie", "biped", 0.78, Vector2(-2.5, -2.0)],
		["imp", "biped", 0.50, Vector2(4.0, 2.2)],
		["bone_hound", "quad", 0.45, Vector2(3.0, -2.5)],
	],
	# Keep great hall — a throne-room gauntlet: golem + acolyte mid-hall,
	# the casters holding the dais at the north (-Z) end.
	"interior": [
		["bone_golem", "biped", 1.10, Vector2(0.0, 1.5)],
		["cultist", "biped", 0.80, Vector2(-1.6, 2.5)],
		["necromancer", "biped", 0.85, Vector2(0.0, -3.0)],
		["skeleton_mage", "biped", 0.80, Vector2(-2.0, -2.4)],
		["lich_king", "biped", 0.95, Vector2(2.0, -2.4)],
	],
	# Village — roaming beasts ambush the player along the road/square.
	"town": [
		["dire_rat", "quad", 0.25, Vector2(-1.5, -3.0)],
		["hell_hound", "quad", 0.50, Vector2(2.0, 0.5)],
		["grave_boar", "quad", 0.45, Vector2(-3.0, 4.0)],
	],
}

static func build(world := "courtyard") -> Node3D:
	var root := Node3D.new()
	root.name = "Bestiary"
	var arena: Vector2 = ARENA.get(world, Vector2(6.0, 6.0))
	for e in POP.get(world, []):
		_spawn_npc(root, e[0], e[1], e[2], e[3], arena)
	return root

static func _spawn_npc(parent: Node3D, cname: String, kind: String, target_h: float, home: Vector2, arena: Vector2) -> void:
	var npc := CharacterBody3D.new()
	npc.name = cname
	npc.set_script(NpcScript)
	npc.cfg = {"name": cname, "kind": kind, "target_h": target_h, "home": home, "arena": arena}
	npc.position = Vector3(home.x, 0.1, home.y)  # floor tile tops sit at ~0.1
	parent.add_child(npc)
