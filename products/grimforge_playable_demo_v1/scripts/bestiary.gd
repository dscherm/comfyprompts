extends Object

# Bestiary population — spawns wandering NPCs (npc.gd) around the castle
# courtyard. Bipeds use the Unity-baked _anim.fbx rig (flavor clip) with the
# KD6 walk clip merged in; quadrupeds use the multi-clip _v2.glb. Each NPC is
# a CharacterBody3D that wanders near its home spot. Bipeds without a walk
# clip (lich_king, skeleton_mage) spawn as stationary idlers.
# Heights are miniature-world targets (kit walls are 1.3m).

const NpcScript := preload("res://scripts/npc.gd")

# name, target height (m), home (x, z)
const BIPEDS := [
	["skeleton_warrior", 0.80, Vector2(0.7, 5.0)],
	["ghoul", 0.75, Vector2(-4.2, 3.2)],
	["cultist", 0.80, Vector2(4.0, -1.0)],
	["plague_zombie", 0.78, Vector2(-2.5, 0.5)],
	["bone_golem", 1.10, Vector2(-3.0, -3.0)],
	["skeleton_mage", 0.80, Vector2(1.8, -4.2)],
	["necromancer", 0.85, Vector2(0.8, -3.4)],
	["lich_king", 0.95, Vector2(0.0, -4.6)],
	["imp", 0.50, Vector2(4.0, 3.4)],
]
const QUADS := [
	["dire_rat", 0.25, Vector2(-1.5, 3.4)],
	["bone_hound", 0.45, Vector2(2.2, 2.0)],
	["hell_hound", 0.50, Vector2(-3.8, -0.8)],
	["grave_boar", 0.45, Vector2(4.4, 1.2)],
]

static func build() -> Node3D:
	var root := Node3D.new()
	root.name = "Bestiary"
	for e in BIPEDS:
		_spawn_npc(root, e[0], "biped", e[1], e[2])
	for e in QUADS:
		_spawn_npc(root, e[0], "quad", e[1], e[2])
	return root

static func _spawn_npc(parent: Node3D, cname: String, kind: String, target_h: float, home: Vector2) -> void:
	var npc := CharacterBody3D.new()
	npc.name = cname
	npc.set_script(NpcScript)
	npc.cfg = {"name": cname, "kind": kind, "target_h": target_h, "home": home}
	npc.position = Vector3(home.x, 0.1, home.y)  # floor tile tops sit at ~0.1
	parent.add_child(npc)
