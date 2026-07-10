extends SceneTree

const EnvBuilder := preload("res://scripts/env.gd")
const PARTS := ["floor_flagstone", "wall", "wall_window", "pillar", "stairs_stone",
	"statue", "brazier", "torch_wall", "gate_arch", "door_arch", "banner",
	"portcullis", "wall_stairs", "balcony", "chapel"]

func _initialize() -> void:
	for m in PARTS:
		var scene: PackedScene = load("res://kit/%s.glb" % m)
		if scene == null:
			print(m, " MISSING (not copied yet)")
			continue
		var inst: Node3D = scene.instantiate()
		var ab := EnvBuilder._subtree_aabb(inst, Transform3D.IDENTITY)
		inst.free()
		print("%s size=%s min=%s" % [m, ab.size, ab.position])
	quit()
