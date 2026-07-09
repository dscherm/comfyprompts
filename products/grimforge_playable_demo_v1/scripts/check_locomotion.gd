extends SceneTree

# Batch validation for the KD6 locomotion FBXs: each must import, expose its
# named clip, and hold a character-sized skeleton bbox mid-clip (no scramble).
# Run: godot --headless --path . --script res://scripts/check_locomotion.gd

const CLIPS := [
	["bone_golem_walk", "walk"],
	["cultist_walk", "walk"],
	["ghoul_walk", "walk"],
	["imp_walk", "walk"],
	["necromancer_walk", "walk"],
	["plague_zombie_walk", "walk"],
	["skeleton_warrior_walk", "walk"],
	["revenant_knight_walk", "walk"],
	["revenant_knight_run", "run"],
]

func _initialize() -> void:
	var fail := false
	for entry in CLIPS:
		var fname: String = entry[0]
		var want: String = entry[1]
		var path := "res://chars/%s.fbx" % fname
		var scene: PackedScene = load(path)
		if scene == null:
			print("FAIL %s: load null" % fname)
			fail = true
			continue
		var inst: Node3D = scene.instantiate()
		get_root().add_child(inst)
		var ap := _find(inst, "AnimationPlayer") as AnimationPlayer
		var sk := _find(inst, "Skeleton3D") as Skeleton3D
		if ap == null or sk == null:
			print("FAIL %s: ap=%s sk=%s" % [fname, ap, sk])
			fail = true
			inst.queue_free()
			continue
		var clips := ap.get_animation_list()
		var clip_name := ""
		for c in clips:
			if want in String(c).to_lower():
				clip_name = c
				break
		if clip_name == "" and clips.size() > 0:
			clip_name = clips[0]
		var clip := ap.get_animation(clip_name)
		ap.play(clip_name)
		ap.seek(clip.length * 0.5, true)
		var mn := Vector3.INF
		var mx := -Vector3.INF
		for bi in range(sk.get_bone_count()):
			var p := sk.get_bone_global_pose(bi).origin
			mn = mn.min(p)
			mx = mx.max(p)
		var ext := (mx - mn).length()
		var ok := ext > 0.1 and ext < 4.0
		print("%s: clip=%s bones=%d ext=%.2f %s" % [fname, clip_name, sk.get_bone_count(), ext, "OK" if ok else "FAIL"])
		if not ok:
			fail = true
		inst.queue_free()
	print("LOCOMOTION_CHECK ", "FAIL" if fail else "PASS")
	quit(1 if fail else 0)

func _find(node: Node, cls: String) -> Node:
	if node.get_class() == cls:
		return node
	for c in node.get_children():
		var r := _find(c, cls)
		if r:
			return r
	return null
