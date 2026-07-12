extends SceneTree

# One-off generator: writes data/enemies/<id>.tres from the roster below, porting
# the CURRENT hardcoded values verbatim (HP from npc.gd ENEMY_HP; DMG from
# ENEMY_DMG with the 9.0 default applied; kind/target_h/home/world from
# bestiary.gd POP). Run once, headless:
#   godot --headless --path . --script res://scripts/_gen_enemy_defs.gd
# The committed artefacts are the .tres files; this script can be deleted after.

const EnemyDefScript := preload("res://scripts/enemy_def.gd")

# id, kind, target_h, hp, dmg, world, home_x, home_z, ranged
const ROWS := [
	["skeleton_warrior", "biped", 0.80, 30.0, 9.0, "courtyard", 0.7, 3.0, false],
	["ghoul", "biped", 0.75, 40.0, 12.0, "courtyard", -4.0, 1.5, false],
	["plague_zombie", "biped", 0.78, 35.0, 9.0, "courtyard", -2.5, -2.0, false],
	["imp", "biped", 0.50, 20.0, 9.0, "courtyard", 4.0, 2.2, false],
	["bone_hound", "quad", 0.45, 30.0, 9.0, "courtyard", 3.0, -2.5, false],
	["bone_golem", "biped", 1.10, 80.0, 18.0, "interior", 0.0, 1.5, false],
	["cultist", "biped", 0.80, 25.0, 9.0, "interior", -1.6, 2.5, false],
	["necromancer", "biped", 0.85, 30.0, 9.0, "interior", 0.0, -3.0, true],
	["skeleton_mage", "biped", 0.80, 45.0, 11.0, "interior", -2.0, -2.4, true],
	["lich_king", "biped", 0.95, 60.0, 15.0, "interior", 2.0, -2.4, true],
	["dire_rat", "quad", 0.25, 15.0, 6.0, "town", -1.5, -3.0, false],
	["hell_hound", "quad", 0.50, 40.0, 12.0, "town", 2.0, 0.5, false],
	["grave_boar", "quad", 0.45, 45.0, 14.0, "town", -3.0, 4.0, false],
]

func _init() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://data/enemies"))
	for r in ROWS:
		var d: Resource = EnemyDefScript.new()
		d.id = r[0]
		d.kind = r[1]
		d.target_h = r[2]
		d.hp = r[3]
		d.dmg = r[4]
		d.world = r[5]
		d.home = Vector2(r[6], r[7])
		d.hostile = true
		d.ranged = r[8]
		var path := "res://data/enemies/%s.tres" % r[0]
		var err := ResourceSaver.save(d, path)
		print("GEN %s -> %s" % [path, err])
	quit()
