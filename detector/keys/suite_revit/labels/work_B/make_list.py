"""Labeller B (pictures first): the openings of 'presidential suite_layout.dwg' (cache suite_revit), written as
../B.json in the format of keys/tower/labels/l29-E-A.json, plus QA pictures with a marker on every listed opening.

  python -B make_list.py            -> ../B.json, marks_overview.png, marks_*.png (close-ups)

Every number below was read from the drawing cache (prims.pkl) with q.py / door_inventory.py / bays.py in this folder
(the queries are quoted in the evidence); nothing here comes from a detector output.
"""
import json, math, pickle, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'B.json'
PKL = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
FLOOR = 'suite_revit'


def op(id_, kind, subtype, a, b, wt, host, evidence, confidence, notes, optional=False, **extra):
    o = {'id': id_, 'floor': FLOOR, 'kind': kind, 'subtype': subtype, 'a': [round(a[0], 4), round(a[1], 4)],
         'b': [round(b[0], 4), round(b[1], 4)], 'width': round(math.dist(a, b), 4), 'wallThickness': wt, 'host': host,
         'evidence': evidence, 'confidence': confidence, 'notes': notes}
    if optional:
        o['optional'] = True
    o.update(extra)
    return o


O = []

# ---------------------------------------------------------------- doors and passages (west to east)
O.append(op('SRB-01', 'door', 'pocket (cavity) sliding door, single leaf 1.00 m',
            (7.4539, 2.2341), (7.4539, 3.3341), 0.20, 'wall',
            "Partition x 7.3539-7.5539 (layer 0: core 7.3789-7.5289 + 25 mm linings). Fill 51B7 ends at y 2.2341; the two "
            "pocket skins (x 7.354-7.419 / 7.489-7.554, fill 51AF) start at y 3.3341. Leaf A-DOOR x 7.4339-7.4739, "
            "y 3.2241-4.2241 (1.00 m) inside the pocket; slide arrow A-DOOR x 7.3239, y 2.4841-3.0841, head north; frames "
            "A-DOOR-FRAM y 2.2341-2.2841 and 3.2841-3.3341; core lines x 7.3789 / 7.5289 run on across the opening.",
            'high',
            "Master bedroom (west) to the dressing area (east). Wall end to wall end 1.10 (frames included); 1.00 between "
            "the frames = the leaf. The upper end of the opening is where the dressing area opens north into the bedroom "
            "foyer (see SRB-23)."))
O.append(op('SRB-02', 'door', 'pocket (cavity) sliding door, single leaf 1.00 m',
            (7.4539, 10.2841), (7.4539, 11.3841), 0.20, 'wall',
            "Partition x 7.3539-7.5539: fill 51AF ends at y 10.2841 (pocket skins y 9.3341-10.2841); leaf A-DOOR "
            "x 7.4339-7.4739, y 9.3941-10.3941 in the pocket; slide arrow A-DOOR x 7.3239, y 11.1341 -> 10.5341 (head "
            "south); frames y 10.2841-10.3341 and 11.3341-11.3841; core lines x 7.3789 / 7.5289 continuous across. North "
            "end = the inner face of the facade lining (layer-0 fill 4DE4, y 11.3841-11.4091; A-WALL facade y 11.409-11.509).",
            'high',
            "Master bedroom (west) to the master bathroom (east), at the north facade. Wall end to facade face 1.10; leaf "
            "1.00 between the frames."))
O.append(op('SRB-03', 'door', 'pocket (cavity) sliding door, single leaf 1.00 m',
            (8.1289, 5.1557), (9.2289, 5.1557), 0.19, 'wall',
            "Wall y 5.0607-5.2507 (layer 0, core y 5.0857-5.2357): fill 51B2 loop1 (x 7.5539-8.1289) ends at x 8.1289, "
            "fill 51B2 loop0 (x 9.2289-11.4866, pocket y 5.1257-5.1957 to x 10.6666) starts at x 9.2289. Leaf A-DOOR "
            "x 9.1189-10.1189, y 5.1407-5.1807 in the pocket; arrow A-DOOR y 5.2907, x 8.3789 -> 8.9789 (head east, in "
            "the bathroom); frames x 8.1289-8.1789 and 9.1789-9.2289; core lines y 5.0857 / 5.2357 run across.",
            'high',
            "Bedroom foyer (south) to the master bathroom (north). Wall end to wall end 1.10; leaf 1.00."))
O.append(op('SRB-04', 'door', 'bi-fold door, 4 panels of 0.564 m drawn folded at the north end',
            (9.4616, 0.9591), (9.4616, 3.1841), 0.15, 'wall',
            "Wall stub x 9.3866-9.5366 (core 9.4116-9.5116 + linings, fills 4DBA/4DCB/4DD2/4DD0) from the south wall "
            "up to y 0.9591; wall y 3.1841-3.3341 (fills 4DCA/4DCD/4DD1, lining 4DCC) starts at x 9.3866. Between them: "
            "8 A-DOOR lines of 0.5637 m (four panels zigzag, x 9.387-9.944, y 2.456-3.232) and a dashed layer-0 track "
            "x 9.4616, y 0.9591-3.1841 (L 2.225) exactly spanning the gap.",
            'high',
            "Dressing area (west) to the walk-in wardrobe (east). The walk-in wardrobe is a room (about 2 x 2.85 m with "
            "hanging rails), so its door is listed as a room door, not casework. Width 2.225 between the stub end and "
            "the wall face (4 x 0.564 = 2.26 of panels)."))
O.append(op('SRB-05', 'door', 'glass swing door 0.70 in a 10 mm glass screen (family IN_SHOWER DOOR1 - Shower door 700x2160), WC compartment',
            (9.5166, 5.3507), (9.5166, 6.0507), 0.10, 'glass',
            "Glass screen x 9.4666-9.5666 (two continuous layer-0 lines, glass x 9.5116-9.5216). Leaf A-DOOR 10 mm, "
            "0.70 m, hinge (9.5116, 5.3507), drawn open 30 deg to (9.1616, 5.9569); dashed 30-deg swing A-DOOR-HDLN "
            "r 0.70 centre (9.5116, 5.3507) ending at (9.5116, 6.0507); glass stub y 5.2507-5.3507 below, fixed glass "
            "y 6.0507-6.9505 above; dashed pull handle A-GENM-HDLN.",
            'medium',
            "Door of the WC compartment (x 9.57-11.49, y 5.25-6.94, WC fixture inside) of the master bathroom. Measured "
            "by its leaf (the 0.10 glass stub beside the hinge is glass wall). Optional: a toilet-compartment door in a "
            "shower-type glass screen, the kind earlier keys left optional (toilet cubicle doors); a 3D build may "
            "treat the whole screen as glass.", optional=True))
O.append(op('SRB-06', 'door', 'glass swing door 0.70 in a 10 mm glass shower screen (family IN_SHOWER DOOR1 - Shower door 700x2160)',
            (9.5166, 7.1655), (9.5166, 7.8655), 0.10, 'glass',
            "Same screen x 9.4666-9.5666. Leaf A-DOOR 0.70, hinge (9.5116, 7.1655), open 30 deg to (9.1616, 7.7717); "
            "dashed swing A-DOOR-HDLN r 0.70 centre (9.5116, 7.1655) to (9.5116, 7.8655); glass stub y 7.0655-7.1655, "
            "fixed glass y 7.8655-9.4341.",
            'medium',
            "First door of the shower (x 9.57-11.49, y 7.07-10.23). Optional: a shower door is part of the shower "
            "screen, which the labelling rules say not to list; kept as optional so that neither finding nor missing "
            "it counts.", optional=True))
O.append(op('SRB-07', 'door', 'glass swing door 0.70 in a 10 mm glass shower screen (family IN_SHOWER DOOR1 - Shower door 700x2160)',
            (9.5166, 9.4341), (9.5166, 10.1341), 0.10, 'glass',
            "Same screen. Leaf A-DOOR 0.70, hinge (9.5116, 10.1341), open 30 deg to (9.1616, 9.5279); dashed swing "
            "A-DOOR-HDLN r 0.70 centre (9.5116, 10.1341) from (9.1616, 9.5279) to (9.5116, 9.4341); fixed glass "
            "y 7.8655-9.4341 below, glass stub y 10.1341-10.2291 above, then the shower's north glass y 10.2291-10.2391.",
            'medium',
            "Second door of the same shower (north end). Optional for the same reason as SRB-06.", optional=True))
O.append(op('SRB-08', 'door', 'single swing, leaf 0.90 (exploded DOOR_SWING_1_SOLID)',
            (11.5616, 3.6974), (11.5616, 4.6974), 0.15, 'wall',
            "Partition x 11.4866-11.6366 (layer 0): fill 51C0 ends at y 3.6974, fill 51B3 starts at y 4.6974. Leaf "
            "A-DOOR 0.90 x 0.04 hinged at (11.5067, 3.7474), drawn open 90 deg to x 10.6067; dashed swing A-DOOR r 0.90 "
            "centre (11.5067, 3.7474); frames A-DOOR-FRAM y 3.6974-3.7474 and 4.6474-4.6974; handle A-DETL-GENF at the "
            "leaf tip. Nothing crosses the opening.",
            'high',
            "Foyer (east) to the bedroom foyer (west); the leaf opens into the bedroom foyer. Wall end to wall end 1.00, "
            "frames included."))
O.append(op('SRB-09', 'door', 'single swing, leaf 0.665 (swing r 0.70)',
            (11.7116, 3.2591), (12.4616, 3.2591), 0.14, 'wall',
            "Wall y 3.1941-3.3341 (core y 3.2091-3.3091, layer 0) between the foyer (north) and the small room south of "
            "it: core fill 4DB8 loop2 (stub x 11.6116-11.7116) ends at x 11.7116, fill 4DB8 loop1 starts at x 12.4616. "
            "Leaf A-DOOR 0.665 hinged at (11.7116, 3.2291), open 90 deg south into the small room; dashed swing A-DOOR "
            "r 0.70 centre (11.7116, 3.2291) to (12.4116, 3.2352); frame lines A-DOOR-FRAM at x 11.7116 and 12.4116 "
            "(return to 12.4616). A layer-0 line y 3.3091 x 11.7616-12.4616 (threshold) and the room-side lining "
            "(y 3.1941-3.2091) run across the opening.",
            'high',
            "Door of the small room x 11.64-13.12, y 1.22-3.19 (toilet-roll holder on its west wall: probably a powder "
            "room). Wall end to wall end 0.75; 0.70 between the frame lines."))
O.append(op('SRB-10', 'door', 'double swing, two leaves 0.865 (exploded DOOR_SWING_DOUBLE), suite entrance',
            (13.2866, 3.2591), (15.0866, 3.2591), 0.125, 'wall',
            "Wall y 3.2091-3.3091 (core) + lining y 3.3091-3.3341 on the foyer side: fill 4DB8 loop1 ends at x 13.2866, "
            "fill 4DB8 loop0 (x 15.0866-15.2366) starts at x 15.0866. Leaves A-DOOR 0.865 x 0.04 hinged at "
            "(13.3216, 3.3091) and (15.0516, 3.3091), drawn open 90 deg north; dashed swings A-DOOR r 0.865 centres "
            "(13.3216, 3.3091) and (15.0516, 3.3091) meeting at x 14.1866; frames x 13.2866-13.3366 and 15.0366-15.0866; "
            "threshold line layer 0 y 3.3091 x 13.3216-15.0516.",
            'high',
            "The suite's entrance from the corridor (south) into the foyer (north). Wall end to wall end 1.80; hinges "
            "1.73 apart."))
O.append(op('SRB-11', 'passage', 'doorless opening with a head drawn (face lines dashed across)',
            (13.1366, 5.1357), (15.1116, 5.1357), 0.15, 'wall',
            "Wall y 5.0607-5.2107 (layer 0): fill 51B6 loop0 (x 11.6366-13.1366) ends at x 13.1366; the L-shaped "
            "partition fill 51B6 loop1 starts at x 15.1116. Across the gap the two face lines go on dashed (layer 0, "
            "'- DASH SMALL', h 5F8F / 5F91, L 1.975) with a dashed end line at x 15.1116: a head over the opening. No "
            "leaf, frame, arc or glazing.",
            'high',
            "Foyer (south) to the living & dining area (north). Wall end to wall end 1.975."))
O.append(op('SRB-12', 'door', 'double swing service door D22 1800x2100 (block SERVICE_SWING_DOUBLE - D22 1800X2100MM-V24), leaves drawn open 35 deg',
            (15.2366, 3.2591), (17.0366, 3.2591), 0.10, 'wall',
            "Block insert (16.1366, 3.2591) rot 180 on A-DOOR: leaves 0.865 hinged at (15.2716, 3.2091) and "
            "(17.0016, 3.2091), drawn open 35 deg south into the corridor, dashed swings r 0.865; three frame lines "
            "A-DOOR-FRAM y 3.2091 / 3.2491 / 3.3091 across the opening. Jambs: layer-0 fill 4DB8 loop0 + A-WALL 540C "
            "(face x 15.2366) and A-WALL 540D x 17.0366-17.1366 (face x 17.0366). Behind it a 0.35 m riser "
            "(y 3.3091-3.6591) with an A-DETL X.",
            'high',
            "Service riser door on the corridor's north side, outside the suite (riser / shaft doors were scored doors "
            "in the tower key). Wall end to wall end 1.80 = the type width."))
O.append(op('SRB-13', 'door', 'single swing service door 850x2400 (block SERVICE_DOOR_SWING_1_SOLID - 850X2400MM_D06), leaf drawn open 35 deg',
            (16.1866, 1.1591), (17.0366, 1.1591), 0.10, 'wall',
            "Block insert (16.6116, 1.1591) rot 0 on A-DOOR: leaf 0.78 hinged at (17.0016, 1.2091), open 35 deg north "
            "into the corridor, dashed swing r 0.78; frame lines y 1.1091 / 1.1691 / 1.2091. Corridor south wall "
            "y 1.1091-1.2091 (A-WALL): jamb fills 5421 loop0 / 541B (face x 16.1866) and 5421 loop1 / 5411 (face "
            "x 17.0366). Behind it a riser x 16.19-17.04, y 0.76-1.11 with a layer-0 X.",
            'high',
            "Service riser door on the corridor's south side, outside the suite. Wall end to wall end 0.85 = the type width."))
O.append(op('SRB-14', 'door', 'single swing unit door D01 1000x2250 (block UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM-3324155)',
            (19.1766, 0.8591), (20.1766, 0.8591), 0.10, 'wall',
            "Block insert (19.6766, 0.8591) rot 0: leaf 0.80 visible (x 20.1016-20.1416, cut by the view crop at "
            "y 0.0086), hinge at x 20.1416, dashed swing r 0.93 centre (20.1416, 0.8091) from (19.2117, 0.8172); frames "
            "at x 19.1766-19.2266 and 20.1266-20.1766. Wall y 0.8091-0.9091 (A-WALL): fills 5422 loop0 (x 19.0866-19.1766) "
            "and loop1 (x 20.1766-20.2616, then the column). Two A-WALL lines y 0.8091 / 0.9091 run between the frames.",
            'high',
            "Door of a neighbouring unit at the back of the corridor alcove (x 19.09-21.94, y 0.81-1.21); opens south "
            "out of the drawing. The leaf and swing are cut by the crop, the jambs are whole. Wall end to wall end 1.00."))
O.append(op('SRB-15', 'door', 'single swing, leaf 0.70 (exploded)',
            (20.5116, 4.4091), (20.5116, 5.2091), 0.175, 'wall',
            "Partition x 20.4366-20.6116 (core 20.4366-20.5866 + BOH-side lining): fill 51BE ends at y 4.4091, fill "
            "51BC (x 20.4116-20.6116) starts at y 5.2091. Leaf A-DOOR 0.70 hinged at (20.5666, 5.1591), open 90 deg "
            "east into the BOH; dashed swing A-DOOR r 0.70 centre (20.5666, 5.1591) to (20.5605, 4.4591); frames "
            "y 4.4091-4.4591 and 5.1591-5.2091; core lines x 20.4366 / 20.5866 continuous across (y 4.4591-5.1591).",
            'high',
            "Bar (west) to the BOH pantry (east). Wall end to wall end 0.80; 0.70 between the frames."))
O.append(op('SRB-16', 'door', 'pocket (cavity) sliding door, single leaf 1.00 m',
            (20.5116, 6.0841), (20.5116, 7.1841), 0.20, 'wall',
            "Partition x 20.4116-20.6116 (core 20.4366-20.5866): fill 51BC ends at y 6.0841, fill 51B9 (pocket skins "
            "y 7.1841-8.0718) starts at y 7.1841. Leaf A-DOOR x 20.4916-20.5316, y 7.0741-8.0741 in the pocket; arrow "
            "A-DOOR x 20.3816, y 6.3341 -> 6.9341 (head north, in the dining area); frames y 6.0841-6.1341 and "
            "7.1341-7.1841; core lines continuous across.",
            'high',
            "Living & dining area (west) to the lobby of bedroom 2 (east). Wall end to wall end 1.10; leaf 1.00."))
O.append(op('SRB-17', 'door', 'single swing, leaf 0.70 (exploded)',
            (20.7116, 3.3591), (21.5116, 3.3591), 0.125, 'wall',
            "Wall y 3.3091-3.4091 (core) + lining y 3.4091-3.4341 (BOH side): fill 4DF8 loop1 (x 20.5866-20.7116) ends "
            "at x 20.7116, fill 4DF8 loop0 starts at x 21.5116. Leaf A-DOOR 0.70 hinged at (20.7616, 3.3891), open "
            "90 deg north into the BOH; dashed swing A-DOOR r 0.70 centre (20.7616, 3.3891); frames x 20.7116-20.7616 "
            "and 21.4616-21.5116; threshold line layer 0 y 3.4091, x 20.7616-21.4616.",
            'high',
            "Corridor (south) to the BOH pantry (north): the service entrance of the suite. Wall end to wall end 0.80."))
O.append(op('SRB-18', 'door', 'single swing unit door D01 1000x2250 (block UNIT_DOOR_SWING_1_SOLID - D01_1000X2250MM-3324157)',
            (20.8466, 0.8591), (21.8466, 0.8591), 0.10, 'wall',
            "Block insert (21.3466, 0.8591) rot 180: leaf visible x 20.8816-20.9216 (cut by the crop at y 0.0086), "
            "hinge at x 20.8816, dashed swing r 0.93 centre (20.8816, 0.8091) to (21.8116, 0.8172); frames x 20.8466-20.8966 "
            "and 21.7966-21.8466. Wall y 0.8091-0.9091 (A-WALL): fills 5423 loop1 (x 20.7616-20.8466, after the column) "
            "and loop0 (x 21.8466-21.9366).",
            'high',
            "Second neighbouring-unit door in the corridor alcove, mirror of SRB-14 across the column. Wall end to wall end 1.00."))
O.append(op('SRB-19', 'door', 'single swing, leaf 0.70 (exploded)',
            (22.8116, 6.0341), (22.8116, 6.8341), 0.175, 'wall',
            "Partition x 22.7116-22.8866 (core 22.7366-22.8866 + lobby-side lining): fill 51FA ends at y 6.0341; the "
            "wall end 51FD (x 22.7366-22.8866, y 6.8341-6.8541) and the north wall 51FC (y 6.8541-6.9941) above. Leaf "
            "A-DOOR 0.70 hinged at (22.8666, 6.7841), open 90 deg east into the room; dashed swing A-DOOR r 0.70 centre "
            "(22.8666, 6.7841) to (22.8605, 6.0841); frames y 6.0341-6.0841 and 6.7841-6.8341.",
            'high',
            "Lobby of bedroom 2 (west) to the unlabelled room x 22.89-24.80, y 3.42-6.85 (probably bedroom 2's "
            "bathroom). Wall end to wall end 0.80."))
O.append(op('SRB-20', 'door', 'glass swing door 0.70 in a 10 mm glass screen (family IN_SHOWER DOOR1 - Shower door 700x2160)',
            (23.0016, 4.7750), (23.7016, 4.7750), 0.10, 'glass',
            "Screen y 4.7241-4.8241 (two layer-0 lines, glass y 4.770-4.780). Glass stub x 22.9016-23.0016; leaf A-DOOR "
            "10 mm, 0.70, hinge (23.0016, 4.7800), open 30 deg to (23.6079, 5.1300); dashed swing A-DOOR-HDLN r 0.70 "
            "centre (23.0016, 4.78) from (23.7016, 4.78); fixed glass x 23.7016-24.7966; dashed handle A-GENM-HDLN.",
            'medium',
            "Glass door into the compartment x 22.9-24.8, y 3.42-4.72 of the bedroom-2 bathroom (no fixtures drawn; "
            "the family is the shower door). Optional: shower / WC-compartment door in a glass screen, as SRB-05 to "
            "SRB-07.", optional=True))
O.append(op('SRB-21', 'door', 'double swing service door D22 1800x2100 (block SERVICE_SWING_DOUBLE - D22 1800X2100MM-V25), cut by the view crop',
            (23.9866, 1.1591), (25.7866, 1.1591), 0.10, 'wall',
            "Block insert (24.8866, 1.1591) rot 0: leaf 0.865 hinged at (24.0216, 1.2091), open 35 deg north; swings "
            "r 0.865 centres (24.0216, 1.2091) and (25.7516, 1.2091) meeting at x 24.8866; the second leaf and the frame "
            "lines stop at the crop x 25.0785. West jamb A-WALL 5414 / 5416, face x 23.9866; the east jamb is outside "
            "the drawing. Riser behind (y 0.7591-1.1091, A-DETL X).",
            'medium',
            "Optional because the opening is cut by the Revit view's crop: only its west 1.09 m (x 23.9866-25.0785) is "
            "in the drawing and its east end cannot be read from wall geometry. b is taken from the block (1.80 type "
            "width, symmetric about the insert x 24.8866).", optional=True))
O.append(op('SRB-22', 'door', 'double swing service door D22 1800x2100 (block SERVICE_SWING_DOUBLE - D22 1800X2100MM-2804302), cut by the view crop',
            (23.9866, 3.2591), (25.7866, 3.2591), 0.10, 'wall',
            "Block insert (24.8866, 3.2591) rot 180: leaf 0.865 hinged at (24.0216, 3.2091), open 35 deg south; swings "
            "r 0.865 centres (24.0216, 3.2091) and (25.7516, 3.2091); second leaf and frame lines cut at x 25.0785. West "
            "jamb: layer-0 fills 4DF8 loop0 / 4DF9 (face x 23.9866); east jamb outside the drawing. Riser behind "
            "(y 3.3091-3.6591, A-DETL X).",
            'medium',
            "Optional for the same reason as SRB-21 (crop at x 25.079): visible part x 23.9866-25.0785; full width from "
            "the block.", optional=True))
O.append(op('SRB-23', 'passage', 'open side of an alcove (no wall, nothing drawn)',
            (7.5539, 3.2591), (9.3866, 3.2591), 0.15, 'wall',
            "Wall y 3.1841-3.3341 (layer 0, fills 4DCA/4DCD/4DD1, lining 4DCC) ends at x 9.3866; west of it nothing "
            "until the face of the partition x 7.3539-7.5539 (which itself holds the pocket door SRB-01 up to y 3.3341). "
            "No head, threshold, leaf or glazing across.",
            'low',
            "The dressing area (x 7.55-9.39, y 0.33-3.18) is open along its whole north side to the bedroom foyer. "
            "Optional: a passage mouth into open space (one side is a wall end, the other the face of a cross wall), "
            "the kind earlier keys left optional.", optional=True))
O.append(op('SRB-24', 'passage', 'open side of a lobby (no wall, nothing drawn)',
            (20.6116, 6.9241), (22.7366, 6.9241), 0.14, 'wall',
            "Wall y 6.8541-6.9941 (layer 0, fill 51FC; the north wall of the room x 22.89-24.80) ends at x 22.7366; west "
            "of it nothing until the face of the partition x 20.4116-20.6116 (which holds the pocket door SRB-16, "
            "y 6.0841-7.1841, at this height).",
            'low',
            "The lobby of bedroom 2 (x 20.61-22.71, y 6.03-6.99, wardrobe on its south side) opens along its whole "
            "north side into bedroom 2. Optional: passage mouth into open space, as SRB-23.", optional=True))

# ---------------------------------------------------------------- curtain-wall bay facets (optional windows)
BAYS = [  # from bays.py: facet ends = faces of the A-WALL pieces (wall ends, 'Walls 13' corner wedges)
    ('west bay', [((2.7970, 2.8944), (1.6263, 4.0651)), ((1.6116, 4.1005), (1.6116, 7.6177)), ((1.6263, 7.6530), (2.7970, 8.8237))]),
]
for k, x0 in enumerate([0.0, 4.375, 8.75, 13.125, 17.5]):
    BAYS.append((f'north bay {k + 1}', [((3.8475 + x0, 11.4961), (4.0563 + x0, 12.2758)),
                                         ((4.0796 + x0, 12.3061), (5.3068 + x0, 13.0148)),
                                         ((5.3448 + x0, 13.0198), (6.1244 + x0, 12.8110))]))
ROOM = {'west bay': 'master bedroom', 'north bay 1': 'master bedroom', 'north bay 2': 'master bathroom (bath)',
        'north bay 3': 'living & dining area', 'north bay 4': 'living & dining area', 'north bay 5': 'bedroom 2'}
n = 0
for bay, facets in BAYS:
    for i, (a, b) in enumerate(facets):
        n += 1
        w = math.dist(a, b)
        pane = min(((0.8071, 0.7071), (1.4172, 1.4172), (1.6556, 1.5556), (3.5172, 3.5172)), key=lambda t: abs(t[0] - w))[1]
        mull = 'its two 50 mm mullion boxes included' if abs(pane - w) > 0.01 else 'between the corner wedges, no mullion box'
        O.append(op(f'SRB-W{n:02d}', 'window', f'fixed curtain-wall glazing, facet {i + 1} of 3 of the {bay} ({w:.3f} m, {mull})',
                    a, b, 0.10, 'wall',
                    f"A-GLAZ-CURT panel (pane {pane:.4f} m, two lines 10 mm apart) with A-GLAZ-CWMG mullion lines 0.10 m "
                    f"apart along it; the facet's ends lie exactly on A-WALL faces (facade wall end, 'Walls 13' corner "
                    f"wedge or the angled solid wall), checked by bays.py.",
                    'low',
                    f"{bay} of the {ROOM[bay]}. Optional: curtain-wall glazing set between solid wall ends; by the glazing-"
                    f"in-a-wall-gap rule a window, by its Revit element a curtain wall (glass wall). The bank key listed "
                    f"this case as optional windows; fixed panes, no opening sash drawn.", optional=True))

# ---------------------------------------------------------------- glass walls, uncertain, rejected
GLASS = [
    {'a': [9.5166, 5.2507], 'b': [9.5166, 10.2391],
     'notes': "Master bathroom glass screen (10 mm glass x 9.5116-9.5216 between continuous layer-0 lines x 9.4666 / "
              "9.5666): glass y 5.2507-5.3507, 6.0507-6.9355, 7.0655-7.1655, 7.8655-9.4341, 10.1341-10.2291; the glass "
              "doors SRB-05/06/07 fill the rest."},
    {'a': [9.5116, 10.2341], 'b': [11.4966, 10.2341],
     'notes': "North side of the shower: 10 mm glass fill (layer 0) y 10.2291-10.2391, x 9.5116-11.4966; no door."},
    {'a': [22.9016, 4.7750], 'b': [24.7966, 4.7750],
     'notes': "Screen of the bedroom-2 bathroom (glass y 4.770-4.780 between layer-0 lines y 4.7241 / 4.8241): "
              "glass x 22.9016-23.0016 and 23.7016-24.7966; glass door SRB-20 between."},
    {'a': [2.7970, 2.8944], 'b': [2.7970, 8.8237],
     'notes': "West bay of the master bedroom: curtain wall of three facets (1.656 / 3.517 / 1.656 m incl. mullion "
              "boxes) at 135 / 90 / 45 deg from the west wall end (2.797, 2.894) via x 1.6116 to the west wall end "
              "(2.797, 8.824); also listed facet by facet as optional windows SRB-W01..W03."},
    {'a': [3.8475, 11.4961], 'b': [23.6244, 12.8110],
     'notes': "Five north bays (bay k: facets 0.807 / 1.417 / 0.807 m at 75 / 30 / -15 deg, k = 1..5 starting at "
              "x 3.8475, 8.2225, 12.5975, 16.9725, 21.3475 on the facade y 11.41-11.51, ending at the angled solid wall); "
              "each listed facet by facet as optional windows SRB-W04..W18. a/b here are only the first and last "
              "facet ends of the whole run."},
]
UNCERTAIN = [
    {'where': [9.5166, 7.8], 'what': "SRB-05/06/07/20: glass doors in 10 mm glass screens (family 'IN_SHOWER DOOR1 - Shower "
     "door_700X2160MM'). Shower doors belong to shower screens (not to be listed) and SRB-05 is the door of a WC "
     "compartment (like a toilet cubicle door), so all four are optional. If the key scores them, the leaf "
     "convention gives 0.70 each."},
    {'where': [24.8866, 2.2], 'what': "SRB-21 / SRB-22: the two D22 service double doors at x 23.99-25.79 are cut by the "
     "view's crop (x 25.079). Width 1.80 and b = 25.7866 come from the block; the drawing shows only 1.09 m of each. "
     "Listed as optional. If scored, the visible-part alternative is a = (23.9866, y), b = (25.0785, y), w 1.092."},
    {'where': [8.47, 3.2591], 'what': "SRB-23 and SRB-24 (optional passages): whole open sides of the dressing area and "
     "of bedroom 2's lobby, 1.83 m and 2.13 m, each between a wall end and the face of a cross wall that carries a "
     "pocket door at that point. They could also be read as no opening at all (one space)."},
    {'where': [13.0, 12.3], 'what': "Curtain-wall bays SRB-W01..W18: listed per facet as optional windows (bank-key "
     "precedent for curtain-wall glazing between solid wall ends). If the key instead treats a bay as one window, its "
     "chord runs wall end to wall end, e.g. north bay 1 (3.8475, 11.4961)-(6.1244, 12.8110), 2.63 m; west bay "
     "(2.7970, 2.8944)-(2.7970, 8.8237), 5.93 m. Under the tower convention they are glass walls only."},
    {'where': [12.0866, 2.2], 'what': "SRB-09: the small room south of the foyer has no fixtures drawn (toilet-roll "
     "holder only); it is listed as a room door, not a cubicle door. Its door is 0.75 between wall ends but "
     "0.70 between the frame lines."},
    {'where': [9.4616, 2.07], 'what': "SRB-04 (bi-fold, 2.225 m) is the door of the walk-in wardrobe; scored as a room "
     "door. If walk-in wardrobes count as casework it would drop."},
]
REJECTED = [
    {'id': 'R-01', 'where': [15.3116, 4.4224], 'reason': "Closed layer-0 outline x 15.1116-15.5116, y 3.7841-5.0607 in the "
     "foyer's east side (no fill, no door drawn): a built-in cupboard / joinery, not a wall gap."},
    {'id': 'R-02', 'where': [14.2866, 1.0341], 'reason': "Fire-hose cabinet (block 'FHC 02 - Type 1', M-EQPM, x 13.89-14.69, "
     "y 0.86-1.21) recessed in the corridor's south wall: a cabinet; the shaft behind it is closed."},
    {'id': 'R-03', 'where': [19.6741, 1.1591], 'reason': "Mouths of the corridor alcove x 19.0866-20.2616 and x 20.7616-21.9366 "
     "(corridor south wall line y 1.1091-1.2091, column between): 0.3 m deep recesses in front of the unit doors "
     "SRB-14 / SRB-18, part of the corridor; the openings are the doors."},
    {'id': 'R-04', 'where': [18.7866, 3.4841], 'reason': "Corridor recess x 17.1366-20.4366, y 3.3091-3.6591 in front of the "
     "bar's south wall: part of the corridor, no wall line across."},
    {'id': 'R-05', 'where': [20.6966, 8.0716], 'reason': "Niche with rounded A-WALL returns and a slatted luggage rack (Q-CASE) "
     "in bedroom 2's west wall, y 7.54-8.61: the partition x 20.4116-20.6116 (fill 51B9) runs on behind it; not a "
     "through opening."},
    {'id': 'R-06', 'where': [7.8616, 11.3966], 'reason': "Break in the 25 mm facade lining x 7.7866-7.9366 (y 11.384-11.409): "
     "the A-WALL facade wall (53F7) is continuous; not an opening."},
    {'id': 'R-07', 'where': [5.2, 0.65], 'reason': "Wardrobe fronts along the master bedroom's south wall (dashed layer-0 "
     "lines x 4.35 / 6.15, y 0.33-0.96), the lobby wardrobe (x 20.61-22.71, y 5.43-6.03) and the walk-in wardrobe "
     "fittings: casework doors, not listed."},
    {'id': 'R-08', 'where': [22.1, 3.75], 'reason': "Fridge with a 0.5 m door swing in the BOH (frozen Q-SPCQ), swing-like "
     "arcs of beds and cushions (I-FURN, A-GENM) and the round-table rims: furniture."},
    {'id': 'R-09', 'where': [13.35, 0.71], 'reason': "Shaft x 12.01-14.69, y 0.41-1.01 (200 mm A-WALL walls): closed on all "
     "sides, no door."},
    {'id': 'R-10', 'where': [17.6, 6.5], 'reason': "Bar and living & dining area: open plan with no wall between them, so no "
     "opening; likewise each bay opens fully into its room (no wall across the bay mouth)."},
]

METHOD = (
    "Labeller B, pictures first. 1) Read description.md, drawing.json and pictures/INDEX.md, then went over "
    "overview_all.png and overview_structure.png and every one of the 18 close-up tiles (A1-F3) room by room, "
    "following every wall line and the whole facade (west bay, five north bays, corridor and crop edges), plus the "
    "eight convention close-ups (pocket, hinged, glass-screen, bi-fold, head-line, service, unit doors, bay); wrote "
    "down every leaf, swing, slide arrow, bi-fold, frame pair, dashed head and open wall end. 2) Then measured each "
    "one from the geometry: door_inventory.py read the DXF with ezdxf (every insert; every arc on A-DOOR / "
    "A-DOOR-HDLN and every swing-like arc on any layer; every A-DOOR line > 0.3 m) - the 16 swings on A-DOOR, the 4 30-degree glass-door swings "
    "on A-DOOR-HDLN, the 4 slide arrows with their 1.0 m leaves and the 8 bi-fold panel lines, all accounted for; q.py listed the cache items "
    "round each opening (fill loops, face lines, frames); a and b are the faces of the wall-fill ends (layer-0 / "
    "A-WALL SOLID hatches) on the wall's core centre line, frames included (wall end to wall end), as in the "
    "earlier keys; doors in glass screens by their leaf; curtain-wall facets from bays.py (panes plus in-line "
    "50 mm mullion boxes, ends checked to lie on A-WALL faces). 3) Checked that every partition / shell wall fill "
    "between the listed openings is continuous (q.py on each wall), and drew marks_overview.png and close-ups with "
    "a marker on every listed opening: no swing, leaf, arrow, track, head or wall gap is left unmarked. "
    "Conventions: corridor doors outside the suite (service risers, neighbouring units) are listed like the tower "
    "key's shaft doors; openings cut by the view crop with an end outside the drawing, doors in shower / WC glass "
    "screens, passage mouths into open space and curtain-wall facets are optional. 'floor' is 'suite_revit' (one "
    "plan per file). No detector output, mapping, blind-run folder or other labeller's work (labels/work_A, work_C) was read. "
    "Widths: wall end to wall end; the clear width between the frame legs is 0.10 less for the doors with 50 mm "
    "frames inside the opening (SRB-01/02/03/08/10/15/16/17/19), 0.05 less for SRB-09.")

FILES = [str(HERE / f) for f in ('q.py', 'door_inventory.py', 'door_inventory.txt', 'bays.py', 'make_list.py',
                                 'marks_overview.png', 'marks_west.png', 'marks_middle.png', 'marks_east.png')]


def write():
    doc = {'openings': O, 'glassWalls': GLASS, 'uncertain': UNCERTAIN, 'rejected': REJECTED, 'method': METHOD, 'files': FILES}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding='utf-8')
    kinds = {}
    for o in O:
        k = (o['kind'], bool(o.get('optional')))
        kinds[k] = kinds.get(k, 0) + 1
    print(OUT, len(O), 'entries', kinds)


def render():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    D = pickle.load(open(PKL, 'rb'))
    items = D['items']
    WALL = {'0', 'A-WALL', 'S-COLS'}
    DOOR = {'A-DOOR', 'A-DOOR-FRAM', 'A-DOOR-HDLN'}
    GL = {'A-GLAZ-CURT', 'A-GLAZ-CWMG'}
    boxes = {'marks_overview': (1.0, -0.5, 26.0, 13.5), 'marks_west': (1.0, -0.3, 12.2, 13.4),
             'marks_middle': (10.8, -0.3, 19.5, 13.4), 'marks_east': (17.5, -0.3, 26.0, 13.4)}
    for name, (x0, y0, x1, y1) in boxes.items():
        w, h = x1 - x0, y1 - y0
        sc = 1.0 if name == 'marks_overview' else 1.6
        fig = plt.figure(figsize=(w * sc, h * sc), dpi=110)
        ax = fig.add_axes([0.03, 0.03, 0.94, 0.94])
        for d in items:
            lay = d['lay']
            if d['t'] in ('INSERT', 'TEXT', 'MTEXT', 'ATTRIB') or lay in ('Q-SPCQ', 'A-ANNO-IDEN'):
                continue
            if d['t'] == 'HATCH':
                if d.get('solid') and lay in WALL:
                    for l in d['loops']:
                        if len(l) > 2:
                            ax.fill([p[0] for p in l], [p[1] for p in l], color='#9a8f86' if lay != 'A-WALL' else '#555555',
                                    lw=0, zorder=1)
                continue
            P = d.get('pts')
            if not P:
                continue
            col, lw, z = '#c9c2bc', 0.4, 0
            if lay in WALL: col, lw, z = '#8a7f76', 0.5, 2
            if lay in DOOR: col, lw, z = '#d62728', 0.8, 3
            if lay in GL: col, lw, z = '#1f9fbf', 0.6, 3
            ls = '--' if d.get('lt') not in (None, 'BYLAYER', 'BYBLOCK', 'Continuous', 'CONTINUOUS') else '-'
            ax.plot([p[0] for p in P], [p[1] for p in P], color=col, lw=lw, ls=ls, zorder=z)
        for o in O:
            (ax_, ay), (bx, by) = o['a'], o['b']
            c = {'door': '#2ca02c', 'passage': '#ff7f0e', 'window': '#9467bd'}[o['kind']]
            ax.plot([ax_, bx], [ay, by], color=c, lw=5 if not o.get('optional') else 3,
                    alpha=0.75 if not o.get('optional') else 0.55, solid_capstyle='butt', zorder=5,
                    ls='-' if not o.get('optional') else (0, (2, 1)))
            for px, py in ((ax_, ay), (bx, by)):
                ax.plot([px], [py], marker='o', ms=3, color='k', zorder=6)
            cx, cy = (ax_ + bx) / 2, (ay + by) / 2
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                ax.text(cx, cy + 0.12, o['id'].replace('SRB-', '') + ('*' if o.get('optional') else ''), fontsize=7 if
                        name == 'marks_overview' else 9, color=c, ha='center', va='bottom', zorder=7,
                        bbox=dict(boxstyle='round,pad=0.1', fc='white', ec='none', alpha=0.7))
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
        ax.grid(True, color='#eeeeee', lw=0.5)
        ax.set_xticks(range(math.ceil(x0), math.floor(x1) + 1)); ax.set_yticks(range(math.ceil(y0), math.floor(y1) + 1))
        ax.set_title(f'Labeller B: listed openings (green door, orange passage, purple window; dashed/* = optional) {name}',
                     fontsize=10)
        fig.savefig(HERE / f'{name}.png')
        plt.close(fig)
        print(HERE / f'{name}.png')


if __name__ == '__main__':
    write()
    if '--no-png' not in sys.argv:
        render()
