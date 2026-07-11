extends Object

# Castle great-hall interior, built at runtime from castle_kit_grimforge_v1
# parts. Reuses env.gd's _place (flat normals + fixed atlas + box colliders).
# A flagstone hall: perimeter walls with windows, a grand entrance arch at the
# south (+Z), two pillar rows flanking a central aisle, and a raised dais with
# a throne idol + banners at the north (-Z). Entrance faces +Z so the courtyard
# keep door (which also faces the player) leads in naturally.

const EnvBuilder := preload("res://scripts/env.gd")

const W := 9    # floor tiles across (x)
const D := 13   # floor tiles deep (z)
const ENTRANCE_HALF := 1.0   # half-width of the south entrance gap

# Where the player should spawn when entering (just inside the south arch),
# and where the exit trigger sits.
static func entrance_point() -> Vector3:
	return Vector3(0.0, 0.1, float(D) * 0.5 - 1.5)

static func build() -> Node3D:
	var root := EnvBuilder._make_nav_region()
	root.name = "Interior"

	var tile := load("res://kit/floor_flagstone.glb")
	var pitch: float = maxf(EnvBuilder._footprint(tile).x, 0.5)
	var hx := float(W) * pitch * 0.5 - pitch * 0.5
	var hz := float(D) * pitch * 0.5 - pitch * 0.5
	var edge_x := hx + pitch * 0.5
	var edge_z := hz + pitch * 0.5

	# --- floor ---
	for gx in range(W):
		for gz in range(D):
			EnvBuilder._place(root, "floor_flagstone", Vector3(float(gx) * pitch - hx, 0.0, float(gz) * pitch - hz), 0.0)

	# --- perimeter walls (seamless), gap at south center for the entrance ---
	var wall_scene := load("res://kit/wall.glb")
	var wpitch: float = maxf(EnvBuilder._footprint(wall_scene).x, 0.5)
	# north (-Z) + south (+Z): span along X
	_wall_run(root, Vector3(0, 0, -edge_z), true, edge_x * 2.0, wpitch, 0.0, false, 0.0)      # north wall, windows
	_wall_run(root, Vector3(0, 0, edge_z), true, edge_x * 2.0, wpitch, 180.0, true, ENTRANCE_HALF)  # south wall, gap
	# west (-X) + east (+X): span along Z, windowed
	_wall_run(root, Vector3(-edge_x, 0, 0), false, edge_z * 2.0, wpitch, 90.0, false, 0.0)
	_wall_run(root, Vector3(edge_x, 0, 0), false, edge_z * 2.0, wpitch, 270.0, false, 0.0)
	for c in [Vector3(-edge_x, 0, -edge_z), Vector3(edge_x, 0, -edge_z), Vector3(-edge_x, 0, edge_z), Vector3(edge_x, 0, edge_z)]:
		EnvBuilder._place(root, "wall_corner", c, 0.0)
	# grand entrance arch at the south gap (decorative, non-solid)
	EnvBuilder._place(root, "gate_arch", Vector3(0.0, 0.0, edge_z), 0.0)

	# --- pillars flanking the central aisle ---
	for side in [-1.0, 1.0]:
		for gz in range(-4, 5, 2):
			EnvBuilder._place(root, "pillar", Vector3(side * 2.5, 0.0, float(gz)), 0.0)

	# --- dais + throne at the north end ---
	EnvBuilder._place(root, "stairs_stone", Vector3(0.0, 0.0, -hz + 1.6), 0.0)   # steps up toward -Z
	EnvBuilder._place(root, "statue", Vector3(0.0, 0.55, -hz + 0.6), 180.0)      # idol on the dais, facing +Z
	EnvBuilder._place(root, "banner", Vector3(-1.0, 0.0, -edge_z + 0.2), 0.0)
	EnvBuilder._place(root, "banner", Vector3(1.0, 0.0, -edge_z + 0.2), 0.0)

	# --- light + dressing ---
	for gz in [-3, 0, 3]:
		EnvBuilder._place(root, "brazier", Vector3(-1.4, 0.0, float(gz)), 0.0)
		EnvBuilder._place(root, "brazier", Vector3(1.4, 0.0, float(gz)), 0.0)
	for gz in [-3, 1]:
		EnvBuilder._place(root, "torch_wall", Vector3(-edge_x + 0.15, 0.0, float(gz)), 90.0)
		EnvBuilder._place(root, "torch_wall", Vector3(edge_x - 0.15, 0.0, float(gz)), 270.0)

	return root

# Place a run of walls along one side. horizontal=true spans X (wall yaw 0/180),
# false spans Z (yaw 90/270). windows sprinkles wall_window every 3rd panel;
# gap leaves a centered opening of half-width gap_half.
static func _wall_run(root: Node3D, center: Vector3, horizontal: bool, span: float, wpitch: float, yaw: float, gap: bool, gap_half: float) -> void:
	var count := int(ceil(span / (wpitch * 0.97)))
	var step := span / float(count)
	var start := -span * 0.5
	for i in range(count + 1):
		var t := start + float(i) * step
		if gap and absf(t) <= gap_half:
			continue
		var model := "wall"
		if not gap and (i % 3 == 1):
			model = "wall_window"
		var pos: Vector3 = center
		if horizontal:
			pos = Vector3(t, center.y, center.z)
		else:
			pos = Vector3(center.x, center.y, t)
		EnvBuilder._place(root, model, pos, yaw)
