# mat_tile dataset manifest

Built 2026-07-16 (TX1). 55 images, 17 material families: asphalt, bark, brick, cobblestone, concrete, dirt, fabric, forest floor, grass, metal, planks, plaster, rock, sand, stone, tiles, wood.

All sources are Poly Haven **CC0** albedo/diffuse maps (unlit by nature —
the 'even top-down lighting' caption describes the rendered look SDXL
should associate with the trigger). Prep: scripts/train_lora/prep_dataset.py
--max-edge 1024, RGB. Captions: short tag style,
`mat_tile, <material>, seamless texture, even top-down lighting`.

| dataset file | material | Poly Haven slug | license | source |
|---|---|---|---|---|
| asphalt__asphalt_floor.png | asphalt | asphalt_floor | CC0 | https://polyhaven.com/a/asphalt_floor |
| bark__bark_brown_01.png | bark | bark_brown_01 | CC0 | https://polyhaven.com/a/bark_brown_01 |
| bark__bark_brown_02.png | bark | bark_brown_02 | CC0 | https://polyhaven.com/a/bark_brown_02 |
| bark__bark_willow.png | bark | bark_willow | CC0 | https://polyhaven.com/a/bark_willow |
| bark__bark_willow_02.png | bark | bark_willow_02 | CC0 | https://polyhaven.com/a/bark_willow_02 |
| bark__japanese_hackberry_bark.png | bark | japanese_hackberry_bark | CC0 | https://polyhaven.com/a/japanese_hackberry_bark |
| brick__brick_4.png | brick | brick_4 | CC0 | https://polyhaven.com/a/brick_4 |
| brick__brick_crosswalk.png | brick | brick_crosswalk | CC0 | https://polyhaven.com/a/brick_crosswalk |
| brick__brick_floor.png | brick | brick_floor | CC0 | https://polyhaven.com/a/brick_floor |
| brick__brick_floor_003.png | brick | brick_floor_003 | CC0 | https://polyhaven.com/a/brick_floor_003 |
| cobblestone__brick_pavement.png | cobblestone | brick_pavement | CC0 | https://polyhaven.com/a/brick_pavement |
| cobblestone__brick_pavement_03.png | cobblestone | brick_pavement_03 | CC0 | https://polyhaven.com/a/brick_pavement_03 |
| cobblestone__cobblestone_03.png | cobblestone | cobblestone_03 | CC0 | https://polyhaven.com/a/cobblestone_03 |
| cobblestone__floor_pattern_02.png | cobblestone | floor_pattern_02 | CC0 | https://polyhaven.com/a/floor_pattern_02 |
| cobblestone__pavement_05.png | cobblestone | pavement_05 | CC0 | https://polyhaven.com/a/pavement_05 |
| concrete__anti_slip_concrete.png | concrete | anti_slip_concrete | CC0 | https://polyhaven.com/a/anti_slip_concrete |
| dirt__brown_mud.png | dirt | brown_mud | CC0 | https://polyhaven.com/a/brown_mud |
| dirt__brown_mud_02.png | dirt | brown_mud_02 | CC0 | https://polyhaven.com/a/brown_mud_02 |
| dirt__brown_mud_03.png | dirt | brown_mud_03 | CC0 | https://polyhaven.com/a/brown_mud_03 |
| dirt__burned_ground_01.png | dirt | burned_ground_01 | CC0 | https://polyhaven.com/a/burned_ground_01 |
| dirt__dirt_aerial_02.png | dirt | dirt_aerial_02 | CC0 | https://polyhaven.com/a/dirt_aerial_02 |
| fabric__brown_leather.png | fabric | brown_leather | CC0 | https://polyhaven.com/a/brown_leather |
| fabric__denim_fabric.png | fabric | denim_fabric | CC0 | https://polyhaven.com/a/denim_fabric |
| fabric__denmin_fabric_02.png | fabric | denmin_fabric_02 | CC0 | https://polyhaven.com/a/denmin_fabric_02 |
| fabric__dirty_carpet.png | fabric | dirty_carpet | CC0 | https://polyhaven.com/a/dirty_carpet |
| fabric__fabric_leather_01.png | fabric | fabric_leather_01 | CC0 | https://polyhaven.com/a/fabric_leather_01 |
| forest_floor__brown_mud_leaves_01.png | forest floor | brown_mud_leaves_01 | CC0 | https://polyhaven.com/a/brown_mud_leaves_01 |
| forest_floor__forest_leaves_02.png | forest floor | forest_leaves_02 | CC0 | https://polyhaven.com/a/forest_leaves_02 |
| grass__aerial_grass_rock.png | grass | aerial_grass_rock | CC0 | https://polyhaven.com/a/aerial_grass_rock |
| metal__corrugated_iron.png | metal | corrugated_iron | CC0 | https://polyhaven.com/a/corrugated_iron |
| metal__metal_grate_rusty.png | metal | metal_grate_rusty | CC0 | https://polyhaven.com/a/metal_grate_rusty |
| metal__metal_plate.png | metal | metal_plate | CC0 | https://polyhaven.com/a/metal_plate |
| metal__metal_plate_02.png | metal | metal_plate_02 | CC0 | https://polyhaven.com/a/metal_plate_02 |
| metal__rust_coarse_01.png | metal | rust_coarse_01 | CC0 | https://polyhaven.com/a/rust_coarse_01 |
| planks__diagonal_parquet.png | planks | diagonal_parquet | CC0 | https://polyhaven.com/a/diagonal_parquet |
| planks__herringbone_parquet.png | planks | herringbone_parquet | CC0 | https://polyhaven.com/a/herringbone_parquet |
| planks__laminate_floor_03.png | planks | laminate_floor_03 | CC0 | https://polyhaven.com/a/laminate_floor_03 |
| planks__rectangular_parquet.png | planks | rectangular_parquet | CC0 | https://polyhaven.com/a/rectangular_parquet |
| plaster__beige_wall_001.png | plaster | beige_wall_001 | CC0 | https://polyhaven.com/a/beige_wall_001 |
| plaster__beige_wall_002.png | plaster | beige_wall_002 | CC0 | https://polyhaven.com/a/beige_wall_002 |
| plaster__blue_plaster_wall.png | plaster | blue_plaster_wall | CC0 | https://polyhaven.com/a/blue_plaster_wall |
| rock__aerial_rocks_01.png | rock | aerial_rocks_01 | CC0 | https://polyhaven.com/a/aerial_rocks_01 |
| rock__coast_land_rocks_01.png | rock | coast_land_rocks_01 | CC0 | https://polyhaven.com/a/coast_land_rocks_01 |
| rock__coast_sand_rocks_02.png | rock | coast_sand_rocks_02 | CC0 | https://polyhaven.com/a/coast_sand_rocks_02 |
| sand__coast_sand_01.png | sand | coast_sand_01 | CC0 | https://polyhaven.com/a/coast_sand_01 |
| sand__coast_sand_03.png | sand | coast_sand_03 | CC0 | https://polyhaven.com/a/coast_sand_03 |
| sand__coast_sand_04.png | sand | coast_sand_04 | CC0 | https://polyhaven.com/a/coast_sand_04 |
| sand__coast_sand_05.png | sand | coast_sand_05 | CC0 | https://polyhaven.com/a/coast_sand_05 |
| stone__old_stone_wall.png | stone | old_stone_wall | CC0 | https://polyhaven.com/a/old_stone_wall |
| stone__old_stone_wall_02.png | stone | old_stone_wall_02 | CC0 | https://polyhaven.com/a/old_stone_wall_02 |
| stone__rock_wall_10.png | stone | rock_wall_10 | CC0 | https://polyhaven.com/a/rock_wall_10 |
| stone__rock_wall_12.png | stone | rock_wall_12 | CC0 | https://polyhaven.com/a/rock_wall_12 |
| stone__rock_wall_16.png | stone | rock_wall_16 | CC0 | https://polyhaven.com/a/rock_wall_16 |
| tiles__blue_floor_tiles_01.png | tiles | blue_floor_tiles_01 | CC0 | https://polyhaven.com/a/blue_floor_tiles_01 |
| wood__old_wood_floor.png | wood | old_wood_floor | CC0 | https://polyhaven.com/a/old_wood_floor |
