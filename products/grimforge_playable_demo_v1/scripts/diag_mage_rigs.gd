extends SceneTree

# Compare the skeletons of the two idler rigs (lich_king, skeleton_mage) against
# a WORKING walk source (skeleton_warrior_walk), to decide whether the warrior's
# walk clip can be retargeted onto the idlers in-Godot (same CC_Base bone names →
# just a node-path remap; see project_godot_cross_fbx_anim_merge).
#   godot --headless --path . --script res://scripts/diag_mage_rigs.gd

func _initialize() -> void:
	var files := {
		"WALK_SRC skeleton_warrior_walk": "res://chars/skeleton_warrior_walk.fbx",
		"IDLE lich_king_anim": "res://chars/lich_king_anim.fbx",
		"IDLE skeleton_mage_anim": "res://chars/skeleton_mage_anim.fbx",
	}
	var bonesets := {}
	for label in files:
		print("\n===== ", label, " =====")
		var scene: PackedScene = load(files[label])
		if scene == null:
			print("  LOAD FAILED")
			continue
		var inst: Node = scene.instantiate()
		var sk := _find(inst, "Skeleton3D") as Skeleton3D
		if sk:
			print("  Skeleton3D '", sk.name, "' bone_count=", sk.get_bone_count())
			var names := []
			for i in range(sk.get_bone_count()):
				names.append(sk.get_bone_name(i))
			bonesets[label] = names
			print("  first 12 bones: ", names.slice(0, 12))
		else:
			print("  NO Skeleton3D")
		var ap := _find(inst, "AnimationPlayer") as AnimationPlayer
		if ap:
			print("  AP.root_node=", ap.root_node, "  clips=", ap.get_animation_list())
			for cl in ap.get_animation_list():
				var a := ap.get_animation(cl)
				print("    clip '", cl, "' tracks=", a.get_track_count(),
					"  len=", a.length)
				if a.get_track_count() > 0:
					print("      track[0] path=", a.track_get_path(0))
				# print the first BONE track (has a subname) to compare full
				# node path down to Skeleton3D across characters
				for ti in range(a.get_track_count()):
					var pp := a.track_get_path(ti)
					if pp.get_subname_count() > 0:
						print("      first bone track=", pp)
						break
		inst.free()
	# Set comparison: is every warrior bone present in each idler?
	var src_key := "WALK_SRC skeleton_warrior_walk"
	if bonesets.has(src_key):
		var src: Array = bonesets[src_key]
		for label in bonesets:
			if label == src_key:
				continue
			var tgt: Array = bonesets[label]
			var missing := []
			for b in src:
				if not (b in tgt):
					missing.append(b)
			var extra := []
			for b in tgt:
				if not (b in src):
					extra.append(b)
			print("\n>>> ", label, ": ", src.size(), " src bones, ",
				tgt.size(), " tgt bones; missing_from_tgt=", missing.size(),
				" extra_in_tgt=", extra.size())
			if missing.size() > 0:
				print("    MISSING: ", missing.slice(0, 20))
			if extra.size() > 0:
				print("    EXTRA: ", extra.slice(0, 20))
	quit()

func _find(node: Node, cls: String) -> Node:
	if node.get_class() == cls:
		return node
	for c in node.get_children():
		var r := _find(c, cls)
		if r:
			return r
	return null
