extends NavigationRegion3D

# Runtime-baked navmesh for a world. The demo assembles all geometry in code
# (no .tscn), so the navmesh is baked at runtime from this region's child kit
# meshes once the region enters the tree — floor tiles become walkable ground,
# building/wall footprints are carved out by the agent radius. NPCs steer along
# NavigationAgent3D paths and fall back to direct steering during the brief
# async-bake window before the map first syncs (see npc.gd::_nav_dir).

func _ready() -> void:
	bake_finished.connect(_on_bake_finished)
	# defer so every placed child is settled in the tree before geometry parse
	call_deferred("bake_navigation_mesh", true)

func _on_bake_finished() -> void:
	var nm := navigation_mesh
	var polys: int = nm.get_polygon_count() if nm != null else 0
	print("NAV_BAKED region=%s polys=%d" % [get_parent().name if get_parent() else "?", polys])
