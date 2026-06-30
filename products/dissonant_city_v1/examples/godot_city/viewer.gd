extends Node3D
# DissonantCity piece browser: cycle pieces one by one on a turntable.
# Left/Right (or A/D) = prev/next piece. Auto-frames + auto-rotates.

const PIECES := [
	"tower_tall_cyan", "tower_tall_purple", "tower_short_pink", "tower_cyl",
	"tower_spiral", "tower_prism", "dome_building", "arcology", "ziggurat",
	"slab_shop_pink", "slab_shop_cyan", "skybridge", "bridge_support",
	"road_straight", "road_corner", "road_junction", "plaza_tile",
	"streetlight", "billboard", "neon_arch", "hover_car", "hover_car2",
	"antenna", "holo_pylon", "fountain_pad", "crystals", "palm_retro", "barrier",
]

var idx := 0
var current: Node3D
var pivot: Node3D
var cam: Camera3D
var label: Label

func _ready() -> void:
	# environment: dark studio + glow so neon blooms
	var we := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.09, 0.09, 0.12)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.35, 0.30, 0.45); env.ambient_light_energy = 0.6
	env.glow_enabled = true; env.glow_intensity = 0.85; env.glow_bloom = 0.2; env.glow_strength = 1.0
	we.environment = env
	add_child(we)

	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-55, 35, 0); key.light_energy = 2.0
	key.light_color = Color(1.0, 0.92, 0.85); add_child(key)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-50, 210, 0); fill.light_energy = 1.0
	fill.light_color = Color(0.55, 0.8, 0.95); fill.shadow_enabled = false; add_child(fill)

	pivot = Node3D.new(); add_child(pivot)
	cam = Camera3D.new(); pivot.add_child(cam)

	var ui := CanvasLayer.new(); add_child(ui)
	label = Label.new(); label.position = Vector2(24, 18)
	label.add_theme_font_size_override("font_size", 26)
	label.add_theme_color_override("font_color", Color(1, 1, 1))
	ui.add_child(label)
	var hint := Label.new(); hint.position = Vector2(24, 54)
	hint.text = "<-  ->  (or A / D) to cycle  -  auto-rotating"
	hint.add_theme_color_override("font_color", Color(0.7, 0.8, 0.9))
	ui.add_child(hint)

	load_piece()

func _piece_aabb(node: Node) -> AABB:
	var box := AABB(); var first := true
	for c in node.find_children("*", "MeshInstance3D", true, false):
		var mi := c as MeshInstance3D
		var a: AABB = mi.global_transform * mi.get_aabb()
		if first: box = a; first = false
		else: box = box.merge(a)
	return box

func load_piece() -> void:
	if current and is_instance_valid(current):
		current.queue_free()
	var ps := load("res://models/%s.glb" % PIECES[idx]) as PackedScene
	current = ps.instantiate()
	add_child(current)
	await get_tree().process_frame   # let transforms settle for AABB
	var box := _piece_aabb(current)
	var ctr := box.get_center()
	var size: float = max(box.size.x, max(box.size.y, box.size.z))
	if size <= 0.0: size = 2.0
	pivot.position = ctr
	cam.position = Vector3(0, size * 0.45, size * 1.9)
	cam.look_at(pivot.global_position, Vector3.UP)
	cam.near = 0.05
	label.text = "%d / %d    %s" % [idx + 1, PIECES.size(), PIECES[idx]]

func _process(delta: float) -> void:
	if pivot:
		pivot.rotation.y += delta * 0.5

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_RIGHT or event.keycode == KEY_D:
			idx = (idx + 1) % PIECES.size(); load_piece()
		elif event.keycode == KEY_LEFT or event.keycode == KEY_A:
			idx = (idx - 1 + PIECES.size()) % PIECES.size(); load_piece()
		elif event.keycode == KEY_ESCAPE:
			get_tree().quit()
