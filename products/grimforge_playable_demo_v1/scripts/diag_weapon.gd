extends SceneTree

# List the knight's hand/finger bones and the sword's AABB, to size + attach.
# Run: godot --headless --path . --script res://scripts/diag_weapon.gd

func _initialize() -> void:
	var kscene: PackedScene = load("res://chars/revenant_knight_idle.fbx")
	var k: Node = kscene.instantiate()
	var sk := _find(k, "Skeleton3D") as Skeleton3D
	print("knight bones=", sk.get_bone_count())
	for bi in range(sk.get_bone_count()):
		var bn := sk.get_bone_name(bi)
		if "hand" in bn.to_lower() or "r_" in bn.to_lower() and ("mid" in bn.to_lower() or "index" in bn.to_lower()):
			print("  ", bi, " ", bn)

	var sscene: PackedScene = load("res://weapons/sword.glb")
	var s: Node = sscene.instantiate()
	var ab := _aabb(s)
	print("sword aabb size=", ab.size, " center=", ab.get_center(), " min=", ab.position)
	print("sword tree:")
	_tree(s, 0)
	quit()

func _tree(n: Node, d: int) -> void:
	print("  ".repeat(d), n.name, " [", n.get_class(), "]")
	for c in n.get_children():
		_tree(c, d + 1)

func _find(node: Node, cls: String) -> Node:
	if node.get_class() == cls:
		return node
	for c in node.get_children():
		var r := _find(c, cls)
		if r:
			return r
	return null

func _aabb(node: Node) -> AABB:
	var result := AABB()
	var first := true
	var stack: Array = [[node, Transform3D.IDENTITY]]
	while not stack.is_empty():
		var top: Array = stack.pop_back()
		var n: Node = top[0]
		var xf: Transform3D = top[1]
		if n is Node3D:
			xf = xf * (n as Node3D).transform
		if n is MeshInstance3D and (n as MeshInstance3D).mesh:
			var ab := xf * (n as MeshInstance3D).mesh.get_aabb()
			result = ab if first else result.merge(ab)
			first = false
		for c in n.get_children():
			stack.push_back([c, xf])
	return result
