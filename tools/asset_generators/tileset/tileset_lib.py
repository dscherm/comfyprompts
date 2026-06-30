"""Shared tile-gen lib: base terrain + Wang transitions + object sprites.
16x16 fantasy RPG, seamless, curated palette."""
import numpy as np, random
S = 16
def C(h): return tuple(int(h[i:i+2],16) for i in (0,2,4))
PAL = {
 "grass":  [C("2c5320"),C("3e7129"),C("57a23a"),C("78c850")],
 "dgrass": [C("24421a"),C("335c22"),C("47802e"),C("5fa23c")],
 "dirt":   [C("4a3526"),C("6b4d33"),C("8a6843"),C("a07d50")],
 "water":  [C("1d3f63"),C("2c6492"),C("3f8cc0"),C("74c2e2")],
 "deep":   [C("13294a"),C("1d3f63"),C("2c6492"),C("3f8cc0")],
 "stone":  [C("34343d"),C("53535d"),C("74747f"),C("9698a3")],
 "sand":   [C("a8924f"),C("c6b673"),C("ddd29a"),C("efe8bf")],
 "cobble": [C("44444e"),C("5e5e69"),C("7c7c88"),C("9a9aa6")],
 "wood":   [C("3d2a18"),C("5a3d22"),C("7a5630")],
}
FLOWER=[C("d24b4b"),C("e0c84b"),C("e8e8e8"),C("a94bd2")]
def rng(s): return random.Random(s)
def fill(ramp,i):
    a=np.zeros((S,S,3),np.uint8); a[:]=ramp[i]; return a
def dither(a,ramp,s,dp=0.18,lp=0.18):
    r=rng(s)
    for y in range(S):
        for x in range(S):
            t=r.random()
            if t<dp: a[y,x]=ramp[0]
            elif t<dp+lp: a[y,x]=ramp[2]
    return a
def grass(s,ramp):
    a=fill(ramp,1); dither(a,ramp,s,0.14,0.22); r=rng(s+1)
    for _ in range(10):
        x,y=r.randrange(S),r.randrange(S); a[y,x]=ramp[3]; a[(y+1)%S,x]=ramp[2]
    for _ in range(4):
        x,y=r.randrange(S),r.randrange(S); a[y,x]=ramp[0]; a[y,(x+1)%S]=ramp[0]
    return a
def dirt(s,ramp):
    a=fill(ramp,1); dither(a,ramp,s,0.2,0.18); r=rng(s+2)
    for _ in range(6): x,y=r.randrange(S),r.randrange(S); a[y,x]=PAL["stone"][1]
    return a
def water(s,ramp):
    a=fill(ramp,1); r=rng(s)
    for y in range(S):
        for x in range(S): a[y,x]=ramp[1] if ((x+y)%4<2) else ramp[0]  # toroidal diagonal
    for _ in range(7):
        x,y=r.randrange(S),r.randrange(S)
        for dx in range(3): a[y,(x+dx)%S]=ramp[3] if dx==1 else ramp[2]
    return a
def stone(s,ramp):
    a=fill(ramp,1); dither(a,ramp,s,0.22,0.18); r=rng(s+3)
    for _ in range(3):
        x,y=r.randrange(S),r.randrange(S)
        for k in range(r.randrange(2,5)): a[(y+k)%S,(x+(k%2))%S]=ramp[0]
    return a
def sand(s,ramp):
    a=fill(ramp,1); dither(a,ramp,s,0.12,0.16)
    for y in range(S):
        off=int(round(2*np.sin(2*np.pi*y/S)))   # period-S sine -> toroidal in y
        for x in range(S):
            if (x+off)%8==0: a[y,x]=ramp[0]      # %8 divides S=16 -> toroidal in x
    return a
def cobble(s,ramp):
    a=fill(ramp,1)
    for by in range(0,S,4):
        for bx in range(0,S,4):
            off=2 if (by//4)%2 else 0; x0=(bx+off)%S
            for yy in range(4):
                for xx in range(4):
                    px,py=(x0+xx)%S,(by+yy)%S; edge=xx==0 or yy==0
                    a[py,px]=ramp[0] if edge else (ramp[2] if (xx+yy)%5==0 else ramp[1])
    return a
def grass_flowers(s,ramp):
    a=grass(s,ramp); r=rng(s+9)
    for _ in range(5): x,y=r.randrange(S),r.randrange(S); a[y,x]=r.choice(FLOWER)
    return a

def base_tiles():
    return {
     "grass":grass(101,PAL["grass"]), "grass_b":grass(201,PAL["grass"]), "grass_c":grass(202,PAL["grass"]),
     "grass_flowers":grass_flowers(102,PAL["grass"]),
     "dark_grass":grass(103,PAL["dgrass"]), "dirt":dirt(104,PAL["dirt"]),
     "water":water(105,PAL["water"]), "deep_water":water(106,PAL["deep"]),
     "stone":stone(107,PAL["stone"]), "sand":sand(108,PAL["sand"]),
     "cobble_path":cobble(109,PAL["cobble"]),
    }

# --- Wang 2-corner transitions: top terrain over base terrain. mask bit: TL=1,TR=2,BR=4,BL=8 (corner is TOP) ---
def wang(top_arr, base_arr, top_ramp, seed):
    """Return dict mask(0..15)->16x16 array. Corner-continuous so it tiles."""
    out={}
    for mask in range(16):
        c=[(mask>>0)&1,(mask>>1)&1,(mask>>2)&1,(mask>>3)&1]  # TL,TR,BR,BL
        a=base_arr.copy(); r=rng(seed*97+mask); istop=np.zeros((S,S),bool)
        for y in range(S):
            for x in range(S):
                u=(x+0.5)/S; v=(y+0.5)/S
                val=c[0]*(1-u)*(1-v)+c[1]*u*(1-v)+c[2]*u*v+c[3]*(1-u)*v
                val+=(r.random()-0.5)*0.30
                if val>=0.5: a[y,x]=top_arr[y,x]; istop[y,x]=True
        # darker top outline where top borders base (4-neigh, wrapped)
        for y in range(S):
            for x in range(S):
                if not istop[y,x]: continue
                if not(istop[(y-1)%S,x] and istop[(y+1)%S,x] and istop[y,(x-1)%S] and istop[y,(x+1)%S]):
                    a[y,x]=top_ramp[0]
        out[mask]=a
    return out

# --- object sprites (RGBA, transparent bg) ---
def rgba(): return np.zeros((S,S,4),np.uint8)
def setpx(a,x,y,col,al=255):
    if 0<=x<S and 0<=y<S: a[y,x]=(col[0],col[1],col[2],al)
def disc(a,cx,cy,rad,col):
    for y in range(S):
        for x in range(S):
            if (x-cx)**2+(y-cy)**2<=rad*rad: setpx(a,x,y,col)
def obj_rock(s):
    a=rgba(); g=PAL["stone"]; disc(a,8,9,4,g[1]); disc(a,8,9,4,g[1])
    for y in range(S):
        for x in range(S):
            if a[y,x,3]:
                if y<8: a[y,x]=(*g[2],255)
                if y>11: a[y,x]=(*g[0],255)
    # outline
    for y in range(S):
        for x in range(S):
            if a[y,x,3] and (a[(y-1)%S,x,3]==0 or a[(y+1)%S,x,3]==0 or a[y,(x-1)%S,3]==0 or a[y,(x+1)%S,3]==0):
                a[y,x]=(20,20,24,255)
    return a
OUTLINE=C("17220f")  # near-black green for silhouettes
def outline_alpha(a,col=OUTLINE):
    """Add a dark outline ring just outside the sprite's alpha silhouette."""
    sil=(a[:,:,3]>0)
    for y in range(S):
        for x in range(S):
            if not sil[y,x]:
                if (sil[(y-1)%S,x] or sil[(y+1)%S,x] or sil[y,(x-1)%S] or sil[y,(x+1)%S]):
                    a[y,x]=(col[0],col[1],col[2],255)
    return a
def obj_bush(s):
    a=rgba(); g=PAL["grass"]
    for cx,cy,rd in [(6,9,3),(10,9,3),(8,7,4)]: disc(a,cx,cy,rd,g[2])  # lighter than ground
    r=rng(s)
    for y in range(S):
        for x in range(S):
            if a[y,x,3]:
                t=r.random()
                if t<0.30: a[y,x]=(*g[3],255)      # highlights
                elif t<0.45: a[y,x]=(*g[1],255)    # shade
                if y>=11: a[y,x]=(*g[0],255)       # bottom shadow
    outline_alpha(a)
    return a
def obj_tree(s):
    a=rgba(); w=PAL["wood"]; g=PAL["grass"]; dg=PAL["dgrass"]
    for y in range(11,16):                          # trunk
        setpx(a,7,y,w[1]); setpx(a,8,y,w[2] if y%2 else w[0])
    for cx,cy,rd in [(8,6,5),(5,8,3),(11,8,3)]: disc(a,cx,cy,rd,dg[2])  # canopy darker than ground
    r=rng(s)
    for y in range(11):
        for x in range(S):
            if a[y,x,3]:
                t=r.random()
                if t<0.30: a[y,x]=(*g[2],255)       # highlight
                elif t<0.45: a[y,x]=(*dg[1],255)    # shade
                if y<3: a[y,x]=(*g[3],255)          # top light
    outline_alpha(a)
    return a
def obj_flowers(s):
    a=rgba(); g=PAL["grass"]; r=rng(s)
    for _ in range(5):
        x,y=r.randrange(2,14),r.randrange(6,14)
        setpx(a,x,y+1,g[2]); setpx(a,x,y,r.choice(FLOWER))
    return a
def obj_mushroom(s):
    a=rgba(); cap=C("c23b3b"); st=C("e8e0c8")
    for x in range(5,11): setpx(a,x,7,cap)
    for x in range(6,10): setpx(a,x,6,cap)
    setpx(a,6,7,(255,255,255)); setpx(a,9,7,(255,255,255)); setpx(a,8,6,(255,255,255))
    setpx(a,7,8,st); setpx(a,8,8,st); setpx(a,7,9,st); setpx(a,8,9,st)
    return a
def obj_sign(s):
    a=rgba(); w=PAL["wood"]
    for y in range(8,15): setpx(a,8,y,w[1])
    for y in range(4,8):
        for x in range(4,12): setpx(a,x,y,w[2] if (x+y)%3 else w[1])
    for x in range(4,12): setpx(a,x,4,w[0]); setpx(a,x,7,w[0])
    return a
def objects():
    return {"rock":obj_rock(1),"bush":obj_bush(2),"tree":obj_tree(3),
            "flowers":obj_flowers(4),"mushroom":obj_mushroom(5),"signpost":obj_sign(6)}
