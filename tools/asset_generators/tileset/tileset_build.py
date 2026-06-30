"""Assemble the full 16x16 fantasy RPG tileset product: base + 3 Wang transition
sets + objects -> atlas + individual tiles + metadata + sample-map mockup + docs."""
import sys, os, json; sys.path.insert(0,".")
import numpy as np
from PIL import Image
import tileset_lib as T
S=T.S
ROOT="D:/Projects/comfyui-toolchain/products/tileset_fantasy_16_v1"
os.makedirs(f"{ROOT}/tiles", exist_ok=True)

def to_rgba(a):
    if a.shape[2]==4: return a
    out=np.dstack([a, np.full((S,S),255,np.uint8)]); return out

B=T.base_tiles()
OBJ=T.objects()
TRANS={
 ("grass","dirt"):  T.wang(B["grass"], B["dirt"],  T.PAL["grass"], 11),
 ("grass","water"): T.wang(B["grass"], B["water"], T.PAL["grass"], 12),
 ("grass","sand"):  T.wang(B["grass"], B["sand"],  T.PAL["grass"], 13),
}

# ---- flat list of (name, category, rgba, meta) ----
entries=[]
for n,a in B.items(): entries.append((n,"terrain",to_rgba(a),{}))
for (top,base),tiles in TRANS.items():
    for m in range(16):
        entries.append((f"trans_{top}_{base}_{m:02d}","transition",to_rgba(tiles[m]),
                        {"autotile":{"top":top,"base":base,"corner_mask":m}}))
for n,a in OBJ.items(): entries.append((n,"object",a.copy(),{}))

# ---- atlas (power-of-2) ----
cols=8
rows=(len(entries)+cols-1)//cols
def p2(v):
    r=1
    while r<v: r*=2
    return r
AW=p2(cols*S); AH=p2(rows*S)
atlas=Image.new("RGBA",(AW,AH),(0,0,0,0))
meta_tiles=[]
for i,(name,cat,rgba,extra) in enumerate(entries):
    x=(i%cols)*S; y=(i//cols)*S
    atlas.alpha_composite(Image.fromarray(rgba,"RGBA"),(x,y))
    Image.fromarray(rgba,"RGBA").save(f"{ROOT}/tiles/{name}.png")
    meta_tiles.append({"name":name,"category":cat,"x":x,"y":y,"w":S,"h":S,**extra})
atlas.save(f"{ROOT}/atlas.png")

json.dump({"tile_size":S,"atlas":"atlas.png","atlas_size":[AW,AH],"columns":cols,
           "count":len(entries),"tiles":meta_tiles},
          open(f"{ROOT}/metadata.json","w"), indent=1)

# ---- sample-map mockup (hero image) ----
MW,MH=22,15
# corner grid (MH+1 x MW+1), default grass
CG=[["grass"]*(MW+1) for _ in range(MH+1)]
def ellipse(cx,cy,rx,ry,val):
    for gy in range(MH+1):
        for gx in range(MW+1):
            if ((gx-cx)/rx)**2+((gy-cy)/ry)**2<=1.0: CG[gy][gx]=val
ellipse(6,10,3.5,2.6,"water")          # pond
ellipse(17,4,2.6,2.0,"sand")           # sand patch (kept away from water)
# winding dirt path (set corner lines)
px=2
for gy in range(MH+1):
    for dx in (-1,0,1):
        gx=px+dx
        if 0<=gx<=MW and CG[gy][gx]=="grass": CG[gy][gx]="dirt"
    px += 1 if gy%2 else 0
    if px> MW-4: px=MW-4

BITS={"TL":1,"TR":2,"BR":4,"BL":8}
import random as _r
GRASS_VARIANTS=["grass","grass_b","grass_c","grass","grass_b","grass_flowers"]  # weighted, flowers rare
def resolve(cx,cy):
    corners={"TL":CG[cy][cx],"TR":CG[cy][cx+1],"BR":CG[cy+1][cx+1],"BL":CG[cy+1][cx]}
    vals=set(corners.values())
    if len(vals)==1:
        v=list(vals)[0]
        if v=="grass":
            return B[_r.Random(cx*131+cy*17).choice(GRASS_VARIANTS)]
        return B.get(v, B["grass"])
    if "grass" in vals and len(vals)==2:
        other=[v for v in vals if v!="grass"][0]
        if ("grass",other) in TRANS:
            mask=sum(BITS[k] for k,v in corners.items() if v=="grass")
            return TRANS[("grass",other)][mask]
    # fallback: majority non-grass base
    from collections import Counter
    common=Counter(corners.values()).most_common(1)[0][0]
    return B.get(common, B["grass"])

mock=Image.new("RGBA",(MW*S,MH*S),(0,0,0,255))
for cy in range(MH):
    for cx in range(MW):
        mock.alpha_composite(Image.fromarray(to_rgba(resolve(cx,cy)),"RGBA"),(cx*S,cy*S))
# scatter objects on grass cells
import random
r=random.Random(7)
def is_grass_cell(cx,cy):
    return all(CG[cy+dy][cx+dx]=="grass" for dy in (0,1) for dx in (0,1))
placed=[("signpost",3,12)]
for _ in range(26):
    cx,cy=r.randrange(1,MW-1),r.randrange(1,MH-1)
    if is_grass_cell(cx,cy):
        placed.append((r.choice(["tree","tree","bush","rock","flowers","mushroom"]),cx,cy))
for n,cx,cy in placed:
    mock.alpha_composite(Image.fromarray(OBJ[n],"RGBA"),(cx*S,cy*S))
mock.convert("RGB").save(f"{ROOT}/mockup.png")
mock.convert("RGB").resize((MW*S*3,MH*S*3),Image.NEAREST).save(f"{ROOT}/mockup_3x.png")

# export the exact map as atlas-coords for a Godot import-test
name2cell={t["name"]:(t["x"]//S, t["y"]//S) for t in meta_tiles}
def resolve_name(cx,cy):
    corners={"TL":CG[cy][cx],"TR":CG[cy][cx+1],"BR":CG[cy+1][cx+1],"BL":CG[cy+1][cx]}
    vals=set(corners.values())
    if len(vals)==1:
        v=list(vals)[0]
        if v=="grass": return _r.Random(cx*131+cy*17).choice(GRASS_VARIANTS)
        return v if v in name2cell else "grass"
    if "grass" in vals and len(vals)==2:
        other=[x for x in vals if x!="grass"][0]
        if ("grass",other) in TRANS:
            return f"trans_grass_{other}_{sum(BITS[k] for k,vv in corners.items() if vv=='grass'):02d}"
    from collections import Counter
    return Counter(corners.values()).most_common(1)[0][0]
cells=[]
for cy in range(MH):
    for cx in range(MW):
        nm=resolve_name(cx,cy); tc=name2cell.get(nm,name2cell["grass"]); cells.append([cx,cy,tc[0],tc[1]])
objcells=[[cx,cy,*name2cell[n]] for n,cx,cy in placed]
json.dump({"map_w":MW,"map_h":MH,"tile":S,"cols":cols,"cells":cells,"objects":objcells},
          open(f"{ROOT}/godot_map.json","w"))

# atlas preview (4x)
Image.open(f"{ROOT}/atlas.png").resize((AW*4,AH*4),Image.NEAREST).save(f"{ROOT}/atlas_4x.png")
print(f"DONE: {len(entries)} tiles | atlas {AW}x{AH} | mockup {MW}x{MH}")
print("terrain:",len(B),"transitions:",sum(len(v) for v in TRANS.values()),"objects:",len(OBJ))
