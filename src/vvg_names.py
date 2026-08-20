# vvg_names - component id -> (group, side)
#
# This file is the one manual step in the whole pipeline. The numbers come
# from the vvg3 overlay maps: open out/map_front_*.png, read the integer on
# each region, and record which muscle it belongs to.
#
# Sides are anatomical. Front view: viewer-left is the subject's RIGHT.
# Back view: viewer-left is the subject's LEFT.
R, L, N = "right", "left", None

FRONT = {}
def f(group, side, *ids):
    for i in ids: FRONT[i] = (group, side)

f("head", N, 1)
f("throat", N, 4)
f("neck", R, 2); f("neck", L, 3)
f("clavicle", R, 7); f("clavicle", L, 8)
f("trapezius", R, 5); f("trapezius", L, 6)
f("deltoid", R, 9, 11); f("deltoid", L, 10, 12)
f("chest", R, 13); f("chest", L, 14)
f("biceps", R, 15); f("biceps", L, 16)
f("brachialis", R, 27); f("brachialis", L, 28)
f("serratus", R, 17, 19, 23, 25, 31); f("serratus", L, 18, 20, 24, 26, 32)
f("abdomen", R, 21, 29, 36, 41); f("abdomen", L, 22, 30, 35, 42)
f("oblique", R, 39); f("oblique", L, 40)
f("forearm", R, 33, 37, 43, 45); f("forearm", L, 34, 38, 44, 46)
f("hand", R, 53); f("hand", L, 54)
f("fingers", R, 55, 59, 61, 63, 67); f("fingers", L, 56, 60, 62, 64, 66)
f("hip-flexor", R, 47); f("hip-flexor", L, 51)
f("adductor", R, 58); f("adductor", L, 57)
f("sartorius", R, 52); f("sartorius", L, 48)
f("quadriceps", R, 50, 68, 69); f("quadriceps", L, 49, 65, 70)
f("knee", R, 71, 73, 75); f("knee", L, 72, 74, 76)
f("shin", R, 78, 81); f("shin", L, 77, 82)
f("calf", R, 79); f("calf", L, 80)
f("ankle", R, 83, 85); f("ankle", L, 84, 86)
f("foot", R, 87, 89); f("foot", L, 88, 90)

BACK = {}
def b(group, side, *ids):
    for i in ids: BACK[i] = (group, side)

b("head", N, 1)
b("neck", L, 4, 2); b("neck", R, 5, 3)
b("trapezius", L, 6); b("trapezius", R, 7)
b("deltoid", L, 8, 10); b("deltoid", R, 9, 11)
b("triceps", L, 12, 17, 18, 20); b("triceps", R, 13, 16, 19, 21)
b("latissimus", L, 14, 27); b("latissimus", R, 15, 28)
b("erector-spinae", L, 22); b("erector-spinae", R, 23)
b("lower-back", L, 33); b("lower-back", R, 34)
b("forearm", L, 24, 30, 32); b("forearm", R, 25, 31, 29)
b("hand", L, 37); b("hand", R, 38)
b("fingers", L, 39, 41, 45, 49, 51); b("fingers", R, 40, 42, 46, 50, 52)
b("glutes", L, 35); b("glutes", R, 36)
b("it-band", L, 48); b("it-band", R, 47)
b("hamstring", L, 43, 53, 55, 57); b("hamstring", R, 44, 54, 56, 58)
b("calf", L, 59, 61); b("calf", R, 60, 62)
b("achilles", L, 63, 65); b("achilles", R, 64, 66)
b("heel", L, 76); b("heel", R, 77)

MAPS = {"front": FRONT, "back": BACK}
