extends SceneTree

# Headless asset probe: prints each env model's AABB size/origin offset.
# Run: godot --headless --path . --script res://scripts/probe.gd

const EnvBuilder := preload("res://scripts/env.gd")

func _initialize() -> void:
	for m in ["floor_cobble", "floor_grass", "floor_flagstone", "wall", "wall_corner", "gatehouse", "keep", "great_hall", "chapel", "stable", "well", "barrel", "tree", "tower_round"]:
		var scene: PackedScene = load("res://kit/%s.glb" % m)
		if scene == null:
			print(m, " MISSING")
			continue
		var inst: Node3D = scene.instantiate()
		var ab := EnvBuilder._subtree_aabb(inst, Transform3D.IDENTITY)
		inst.free()
		print("%s size=%s origin_min=%s" % [m, ab.size, ab.position])
	quit()
