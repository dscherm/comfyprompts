extends SceneTree

# Dump node tree + animation track paths for the _anim and _walk FBX of one
# character, to design the merge remap. Run:
#   godot --headless --path . --script res://scripts/diag_tracks.gd

func _initialize() -> void:
	for f in ["skeleton_warrior_anim", "skeleton_warrior_walk"]:
		print("\n===== ", f, " =====")
		var scene: PackedScene = load("res://chars/%s.fbx" % f)
		var inst: Node = scene.instantiate()
		print("root node name: ", inst.name, " (", inst.get_class(), ")")
		_dump_tree(inst, 0, 3)
		var ap := _find(inst, "AnimationPlayer") as AnimationPlayer
		if ap:
			print("AnimationPlayer.root_node = ", ap.root_node)
			for cl in ap.get_animation_list():
				var a := ap.get_animation(cl)
				print("  clip '", cl, "' tracks=", a.get_track_count())
				for ti in range(min(3, a.get_track_count())):
					print("    track[", ti, "] = ", a.track_get_path(ti))
	quit()

func _dump_tree(n: Node, depth: int, maxd: int) -> void:
	if depth > maxd:
		return
	print("  ".repeat(depth), n.name, " [", n.get_class(), "]")
	for c in n.get_children():
		_dump_tree(c, depth + 1, maxd)

func _find(node: Node, cls: String) -> Node:
	if node.get_class() == cls:
		return node
	for c in node.get_children():
		var r := _find(c, cls)
		if r:
			return r
	return null
