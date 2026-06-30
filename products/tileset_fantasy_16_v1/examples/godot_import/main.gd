extends Node2D

const OUT := "C:/Users/scher/AppData/Local/Temp/claude/D--Projects-comfyui-toolchain/25899eda-2041-4e64-a0a8-0c83c9100526/scratchpad/godot_render.png"

func _ready() -> void:
	var tex: Texture2D = load("res://atlas.png")
	var ts := TileSet.new()
	ts.tile_size = Vector2i(16, 16)
	var src := TileSetAtlasSource.new()
	src.texture = tex
	src.texture_region_size = Vector2i(16, 16)
	ts.add_source(src, 0)
	var cols := int(tex.get_width() / 16)
	var rows := int(tex.get_height() / 16)
	for ty in rows:
		for tx in cols:
			src.create_tile(Vector2i(tx, ty))

	var terrain := TileMapLayer.new()
	terrain.tile_set = ts
	add_child(terrain)
	var objects := TileMapLayer.new()
	objects.tile_set = ts
	add_child(objects)

	var f := FileAccess.open("res://map.json", FileAccess.READ)
	var data: Dictionary = JSON.parse_string(f.get_as_text())
	var placed := 0
	for c in data["cells"]:
		terrain.set_cell(Vector2i(int(c[0]), int(c[1])), 0, Vector2i(int(c[2]), int(c[3])))
		placed += 1
	for o in data["objects"]:
		objects.set_cell(Vector2i(int(o[0]), int(o[1])), 0, Vector2i(int(o[2]), int(o[3])))
	print("PLACED terrain cells: ", placed, "  objects: ", data["objects"].size())

	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var err := img.save_png(OUT)
	print("CAPTURE err=", err, " -> ", OUT, " size=", img.get_size())
	get_tree().quit()
