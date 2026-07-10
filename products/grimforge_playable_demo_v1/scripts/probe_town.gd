extends SceneTree

const EnvBuilder := preload("res://scripts/env.gd")
const PARTS := ["ground_dirt", "ground_grass", "ground_cobble", "road_straight",
	"path_straight", "cottage", "house_small", "house_tall", "tavern",
	"blacksmith", "church", "well", "market_stall", "fence", "lamppost",
	"signpost", "tree", "wall", "wall_gate", "tower"]

func _initialize() -> void:
	for m in PARTS:
		var scene: PackedScene = load("res://town/%s.glb" % m)
		if scene == null:
			print(m, " MISSING")
			continue
		var inst: Node3D = scene.instantiate()
		var ab := EnvBuilder._subtree_aabb(inst, Transform3D.IDENTITY)
		inst.free()
		print("%s size=%s min=%s" % [m, ab.size, ab.position])
	quit()
