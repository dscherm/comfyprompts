class_name EnemyDef
extends Resource

# Data-driven bestiary entry. One .tres per creature lives under data/enemies/;
# bestiary.gd scans that dir, groups by world, and spawns npc.gd from these
# fields. Adding a creature = adding a .tres, not editing code.

@export var id := ""                 # creature name (matches chars/<id>_*.fbx / _v2.glb)
@export var kind := "biped"          # "biped" | "quad"
@export var target_h := 0.8          # miniature-world height (m); walls are 1.3m
@export var hp := 30.0               # max health
@export var dmg := 9.0               # damage per hit
@export var world := "courtyard"     # "courtyard" | "interior" | "town" | "occult_town"
@export var home := Vector2.ZERO     # wander anchor (x, z)
@export var hostile := true          # joins the "enemy" group and fights
@export var ranged := false          # casters: fire a projectile instead of a melee lunge
