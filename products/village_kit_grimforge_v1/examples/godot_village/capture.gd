extends Node
# Renders village.tscn to verify_shot.png for visual verification, then quits.
# Run windowed (real renderer): godot --path <proj> res://capture.tscn
func _ready() -> void:
	var scn := (load("res://village.tscn") as PackedScene).instantiate()
	add_child(scn)
	# activate the kit's camera
	for c in scn.find_children("*", "Camera3D", true, false):
		(c as Camera3D).make_current()
		break
	await get_tree().process_frame
	await get_tree().process_frame
	await get_tree().create_timer(0.6).timeout
	var img := get_viewport().get_texture().get_image()
	img.save_png("res://verify_shot.png")
	print("SHOT saved verify_shot.png ", img.get_width(), "x", img.get_height())
	get_tree().quit()
