# Role-judge rubric experiment: the vectors

Written by [role_rubric_experiment.py](../../../data_analysis/role_rubric_experiment.py) `analyze-vectors` on 2026-10-22T22:59:24+00:00 (min_count 30, reduce_questions 1; vectors computed from the activations); every number is in [vector_analysis.json](./vector_analysis.json).

Each arm's role vector v_arm is computed as step 4 computes it (the mean of the activations of the responses scored 3, float64, stored float32) and compared with the same role's A0 vector by the centred cosine cos(v_arm − r, v_A0 − r) over the hidden dimension, per slot and layer, for a reference r that is the same for every arm: the median of the A0 role vectors first, then the default vector.  In each table a cell is the median over roles of the role's cosine averaged over layers, and in brackets the median over roles of (1 − cos) divided by A0' 's (1 − cos) for the same role and slot: above 1, the arm turns the role's offset from r more than the judge's own noise does (a role whose A0' vector equals its A0 vector has no noise and no ratio).  An arm below min_count for a role has no vector there and is left out (the last table).

Raw cosines, cos(v_arm, v_A0), are not shown: every role vector shares a large common component, so they are all above 0.9999 and say nothing.  They stay in the JSON (`raw_cos_with_A0`, `summary.raw`), marked as not informative.

## Median reference

r is the elementwise median of the A0 vectors of 30 roles, per slot and layer, the same for every arm.  A role's A0 offset from it, |v_A0 − r|, is a median 15.6% of the vector's length |v_A0| (by slot, 8.1% to 21.1%).

### All roles (30)

| arm | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| A0' | 0.99961 (1.0×) | 0.99943 (1.0×) | 0.99964 (1.0×) | 0.99953 (1.0×) | 0.99926 (1.0×) | 0.99954 (1.0×) | 0.99947 (1.0×) | 0.99956 (1.0×) |
| A1 | 0.99943 (1.0×) | 0.99928 (1.1×) | 0.99952 (1.0×) | 0.99942 (1.0×) | 0.99929 (1.1×) | 0.99946 (1.0×) | 0.99944 (1.1×) | 0.99948 (1.1×) |
| A2 | 0.99945 (1.2×) | 0.99934 (1.2×) | 0.99955 (1.3×) | 0.99935 (1.3×) | 0.99907 (1.4×) | 0.99943 (1.2×) | 0.99934 (1.2×) | 0.99951 (1.3×) |
| A3 | 0.99933 (1.6×) | 0.99940 (1.2×) | 0.99951 (1.1×) | 0.99946 (1.2×) | 0.99918 (1.1×) | 0.99948 (1.2×) | 0.99941 (1.2×) | 0.99953 (1.2×) |
| A4 | 0.99918 (1.8×) | 0.99918 (2.2×) | 0.99926 (1.8×) | 0.99909 (1.9×) | 0.99919 (1.6×) | 0.99920 (1.8×) | 0.99917 (1.8×) | 0.99917 (1.8×) |
| A5 | 0.99927 (1.6×) | 0.99931 (1.4×) | 0.99918 (1.3×) | 0.99911 (1.4×) | 0.99912 (1.3×) | 0.99934 (1.4×) | 0.99921 (1.4×) | 0.99941 (1.5×) |
| A6 | 0.99926 (1.3×) | 0.99932 (1.1×) | 0.99951 (1.0×) | 0.99936 (1.0×) | 0.99914 (1.0×) | 0.99942 (1.0×) | 0.99939 (1.0×) | 0.99950 (1.0×) |
| A7 | 0.99683 (4.3×) | 0.99723 (2.9×) | 0.99725 (3.0×) | 0.99642 (3.4×) | 0.99656 (2.6×) | 0.99699 (3.3×) | 0.99710 (2.7×) | 0.99674 (2.9×) |

### The AI-persona roles (5)

| arm | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| A0' | 0.99990 (1.0×) | 0.99989 (1.0×) | 0.99992 (1.0×) | 0.99992 (1.0×) | 0.99988 (1.0×) | 0.99994 (1.0×) | 0.99992 (1.0×) | 0.99993 (1.0×) |
| A1 | 0.99974 (1.2×) | 0.99984 (1.2×) | 0.99994 (1.4×) | 0.99993 (1.5×) | 0.99989 (1.3×) | 0.99992 (1.5×) | 0.99982 (1.3×) | 0.99986 (1.5×) |
| A2 | 0.99981 (1.4×) | 0.99989 (1.0×) | 0.99990 (1.4×) | 0.99984 (1.3×) | 0.99989 (1.6×) | 0.99991 (1.8×) | 0.99990 (1.6×) | 0.99992 (1.4×) |
| A3 | 0.99972 (1.1×) | 0.99982 (0.6×) | 0.99984 (1.1×) | 0.99976 (1.0×) | 0.99985 (1.1×) | 0.99987 (1.0×) | 0.99985 (0.9×) | 0.99988 (1.1×) |
| A4 | 0.99983 (1.4×) | 0.99980 (1.8×) | 0.99986 (1.7×) | 0.99983 (1.9×) | 0.99979 (1.8×) | 0.99990 (1.7×) | 0.99987 (1.9×) | 0.99992 (1.6×) |
| A5 | 0.99985 (1.5×) | 0.99987 (1.2×) | 0.99988 (1.4×) | 0.99988 (1.5×) | 0.99985 (1.3×) | 0.99991 (1.5×) | 0.99987 (1.5×) | 0.99991 (1.4×) |
| A6 | 0.99981 (1.4×) | 0.99989 (0.8×) | 0.99989 (1.8×) | 0.99984 (1.9×) | 0.99986 (1.7×) | 0.99990 (1.8×) | 0.99990 (1.4×) | 0.99992 (1.4×) |
| A7 | 0.98743 (5.2×) | 0.99411 (1.5×) | 0.99617 (3.3×) | 0.99439 (3.1×) | 0.99419 (2.4×) | 0.99466 (3.2×) | 0.99390 (2.9×) | 0.99525 (3.2×) |

### The other roles (25)

| arm | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| A0' | 0.99959 (1.0×) | 0.99933 (1.0×) | 0.99964 (1.0×) | 0.99951 (1.0×) | 0.99926 (1.0×) | 0.99953 (1.0×) | 0.99932 (1.0×) | 0.99949 (1.0×) |
| A1 | 0.99927 (1.0×) | 0.99918 (1.1×) | 0.99952 (0.9×) | 0.99937 (1.0×) | 0.99924 (1.1×) | 0.99945 (1.0×) | 0.99935 (1.0×) | 0.99945 (1.1×) |
| A2 | 0.99945 (1.1×) | 0.99934 (1.2×) | 0.99954 (1.3×) | 0.99933 (1.3×) | 0.99899 (1.3×) | 0.99942 (1.2×) | 0.99933 (1.2×) | 0.99950 (1.3×) |
| A3 | 0.99930 (1.6×) | 0.99938 (1.2×) | 0.99942 (1.2×) | 0.99941 (1.2×) | 0.99914 (1.1×) | 0.99941 (1.2×) | 0.99941 (1.3×) | 0.99946 (1.2×) |
| A4 | 0.99917 (1.9×) | 0.99915 (2.2×) | 0.99925 (1.9×) | 0.99903 (2.0×) | 0.99910 (1.6×) | 0.99918 (1.8×) | 0.99912 (1.7×) | 0.99912 (2.0×) |
| A5 | 0.99909 (1.7×) | 0.99925 (1.4×) | 0.99892 (1.3×) | 0.99894 (1.3×) | 0.99911 (1.3×) | 0.99931 (1.4×) | 0.99907 (1.4×) | 0.99934 (1.5×) |
| A6 | 0.99914 (1.2×) | 0.99925 (1.1×) | 0.99950 (1.0×) | 0.99930 (1.0×) | 0.99901 (1.0×) | 0.99939 (1.0×) | 0.99937 (1.0×) | 0.99949 (1.0×) |
| A7 | 0.99689 (3.6×) | 0.99776 (2.9×) | 0.99747 (2.7×) | 0.99669 (3.6×) | 0.99716 (2.7×) | 0.99725 (3.4×) | 0.99715 (2.6×) | 0.99709 (2.6×) |

### Offset length, all roles

The median over roles of |v_arm − r| / |v_A0 − r| per slot, averaged over layers: below 1 the arm's selection shortens the role's offset from r, above 1 lengthens it (the two subsets are in the JSON).

| arm | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| A0' | 0.9998 | 1.0001 | 0.9996 | 0.9997 | 0.9996 | 0.9998 | 0.9999 | 0.9998 |
| A1 | 0.9991 | 0.9993 | 0.9992 | 0.9988 | 0.9993 | 0.9995 | 0.9995 | 0.9995 |
| A2 | 1.0017 | 0.9999 | 0.9997 | 0.9998 | 0.9994 | 0.9996 | 1.0000 | 1.0001 |
| A3 | 1.0007 | 1.0001 | 0.9996 | 1.0002 | 0.9996 | 1.0000 | 0.9995 | 1.0001 |
| A4 | 1.0066 | 1.0026 | 0.9999 | 0.9997 | 1.0000 | 1.0001 | 1.0014 | 1.0005 |
| A5 | 1.0004 | 1.0002 | 0.9994 | 0.9997 | 0.9986 | 0.9998 | 0.9997 | 0.9997 |
| A6 | 1.0036 | 1.0002 | 0.9997 | 1.0005 | 1.0011 | 1.0006 | 1.0008 | 0.9999 |
| A7 | 1.0064 | 1.0023 | 1.0000 | 1.0029 | 1.0017 | 1.0004 | 1.0030 | 0.9999 |

### The roles that move most

Per arm, the 5 roles with the largest (1 − cos) relative to A0' 's, both averaged over layers and slots; every role, with its cosine, A0' 's and the offset length, is in the JSON (`moved_roles`).

| arm | roles |
|---|---|
| A1 | [assistant](../../../data/roles/instructions/assistant.json) 3.4×, [psychologist](../../../data/roles/instructions/psychologist.json) 2.3×, [robot](../../../data/roles/instructions/robot.json) 2.0×, [merchant](../../../data/roles/instructions/merchant.json) 1.6×, [historian](../../../data/roles/instructions/historian.json) 1.5× |
| A2 | [ghost](../../../data/roles/instructions/ghost.json) 2.5×, [pirate](../../../data/roles/instructions/pirate.json) 2.4×, [cyborg](../../../data/roles/instructions/cyborg.json) 2.0×, [merchant](../../../data/roles/instructions/merchant.json) 2.0×, [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) 1.6× |
| A3 | [realist](../../../data/roles/instructions/realist.json) 8.2×, [cyborg](../../../data/roles/instructions/cyborg.json) 3.0×, [spirit](../../../data/roles/instructions/spirit.json) 2.8×, [interpreter](../../../data/roles/instructions/interpreter.json) 2.7×, [organizer](../../../data/roles/instructions/organizer.json) 2.5× |
| A4 | [organizer](../../../data/roles/instructions/organizer.json) 5.3×, [realist](../../../data/roles/instructions/realist.json) 4.7×, [robot](../../../data/roles/instructions/robot.json) 4.0×, [peacekeeper](../../../data/roles/instructions/peacekeeper.json) 3.4×, [psychologist](../../../data/roles/instructions/psychologist.json) 3.2× |
| A5 | [realist](../../../data/roles/instructions/realist.json) 8.4×, [organizer](../../../data/roles/instructions/organizer.json) 5.0×, [peacekeeper](../../../data/roles/instructions/peacekeeper.json) 3.0×, [contrarian](../../../data/roles/instructions/contrarian.json) 2.5×, [merchant](../../../data/roles/instructions/merchant.json) 2.4× |
| A6 | [merchant](../../../data/roles/instructions/merchant.json) 2.3×, [cyborg](../../../data/roles/instructions/cyborg.json) 2.1×, [peacekeeper](../../../data/roles/instructions/peacekeeper.json) 2.1×, [assistant](../../../data/roles/instructions/assistant.json) 1.9×, [psychologist](../../../data/roles/instructions/psychologist.json) 1.7× |
| A7 | [assistant](../../../data/roles/instructions/assistant.json) 509.1×, [organizer](../../../data/roles/instructions/organizer.json) 35.1×, [realist](../../../data/roles/instructions/realist.json) 29.4×, [interpreter](../../../data/roles/instructions/interpreter.json) 28.6×, [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) 22.0× |

## Default reference

r is the default entity's step-4 vector (the mean of all its activations; stored float32, its file and sha256 in the JSON), the same for every arm.  A role's A0 offset from it, |v_A0 − r|, is a median 26.1% of the vector's length |v_A0| (by slot, 13.5% to 33.2%).

### All roles (30)

| arm | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| A0' | 0.99952 (1.0×) | 0.99986 (1.0×) | 0.99991 (1.0×) | 0.99990 (1.0×) | 0.99994 (1.0×) | 0.99991 (1.0×) | 0.99983 (1.0×) | 0.99988 (1.0×) |
| A1 | 0.99952 (1.0×) | 0.99982 (1.1×) | 0.99990 (1.0×) | 0.99987 (1.0×) | 0.99993 (1.1×) | 0.99989 (1.0×) | 0.99981 (1.1×) | 0.99984 (1.1×) |
| A2 | 0.99957 (1.2×) | 0.99985 (1.2×) | 0.99989 (1.3×) | 0.99987 (1.3×) | 0.99993 (1.4×) | 0.99990 (1.3×) | 0.99982 (1.2×) | 0.99988 (1.3×) |
| A3 | 0.99932 (1.5×) | 0.99983 (1.2×) | 0.99991 (1.1×) | 0.99989 (1.2×) | 0.99994 (1.1×) | 0.99992 (1.2×) | 0.99981 (1.2×) | 0.99988 (1.2×) |
| A4 | 0.99917 (1.5×) | 0.99979 (2.1×) | 0.99986 (1.9×) | 0.99982 (1.9×) | 0.99991 (1.6×) | 0.99987 (1.8×) | 0.99975 (1.7×) | 0.99982 (1.9×) |
| A5 | 0.99914 (1.7×) | 0.99984 (1.4×) | 0.99986 (1.4×) | 0.99983 (1.4×) | 0.99992 (1.3×) | 0.99988 (1.4×) | 0.99976 (1.4×) | 0.99984 (1.5×) |
| A6 | 0.99942 (1.3×) | 0.99987 (1.1×) | 0.99990 (1.0×) | 0.99988 (1.0×) | 0.99993 (1.0×) | 0.99989 (1.0×) | 0.99979 (1.0×) | 0.99987 (1.1×) |
| A7 | 0.99750 (3.7×) | 0.99935 (2.8×) | 0.99938 (3.3×) | 0.99918 (3.7×) | 0.99961 (3.2×) | 0.99938 (3.5×) | 0.99902 (2.6×) | 0.99892 (3.0×) |

### The AI-persona roles (5)

| arm | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| A0' | 0.99925 (1.0×) | 0.99955 (1.0×) | 0.99997 (1.0×) | 0.99997 (1.0×) | 0.99998 (1.0×) | 0.99998 (1.0×) | 0.99997 (1.0×) | 0.99997 (1.0×) |
| A1 | 0.99700 (1.4×) | 0.99881 (1.2×) | 0.99996 (1.4×) | 0.99995 (1.4×) | 0.99997 (1.3×) | 0.99994 (1.3×) | 0.99985 (1.2×) | 0.99985 (1.3×) |
| A2 | 0.99891 (1.5×) | 0.99925 (1.1×) | 0.99998 (1.5×) | 0.99997 (1.5×) | 0.99998 (1.4×) | 0.99998 (1.3×) | 0.99995 (1.4×) | 0.99995 (1.5×) |
| A3 | 0.99912 (1.2×) | 0.99944 (0.8×) | 0.99997 (1.2×) | 0.99996 (1.1×) | 0.99998 (1.0×) | 0.99998 (1.1×) | 0.99995 (0.9×) | 0.99996 (1.1×) |
| A4 | 0.99880 (1.5×) | 0.99934 (1.7×) | 0.99995 (1.8×) | 0.99996 (1.8×) | 0.99997 (1.6×) | 0.99997 (1.7×) | 0.99994 (1.8×) | 0.99994 (1.7×) |
| A5 | 0.99845 (1.4×) | 0.99903 (1.4×) | 0.99996 (1.5×) | 0.99996 (1.5×) | 0.99998 (1.3×) | 0.99996 (1.4×) | 0.99991 (1.5×) | 0.99990 (1.4×) |
| A6 | 0.99860 (1.5×) | 0.99932 (1.3×) | 0.99998 (1.9×) | 0.99997 (1.9×) | 0.99997 (1.7×) | 0.99997 (1.9×) | 0.99995 (1.5×) | 0.99995 (1.3×) |
| A7 | 0.98523 (4.9×) | 0.99729 (2.0×) | 0.99779 (3.7×) | 0.99717 (3.7×) | 0.99824 (3.2×) | 0.99728 (3.6×) | 0.99605 (3.0×) | 0.99717 (3.5×) |

### The other roles (25)

| arm | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| A0' | 0.99957 (1.0×) | 0.99986 (1.0×) | 0.99991 (1.0×) | 0.99988 (1.0×) | 0.99993 (1.0×) | 0.99989 (1.0×) | 0.99981 (1.0×) | 0.99985 (1.0×) |
| A1 | 0.99952 (1.0×) | 0.99986 (1.1×) | 0.99988 (0.9×) | 0.99986 (1.0×) | 0.99991 (1.1×) | 0.99988 (1.0×) | 0.99976 (1.0×) | 0.99982 (1.1×) |
| A2 | 0.99970 (1.2×) | 0.99987 (1.2×) | 0.99988 (1.3×) | 0.99987 (1.2×) | 0.99992 (1.3×) | 0.99989 (1.2×) | 0.99981 (1.2×) | 0.99988 (1.3×) |
| A3 | 0.99952 (1.6×) | 0.99983 (1.2×) | 0.99989 (1.1×) | 0.99986 (1.2×) | 0.99992 (1.1×) | 0.99990 (1.2×) | 0.99978 (1.3×) | 0.99985 (1.3×) |
| A4 | 0.99946 (1.5×) | 0.99982 (2.1×) | 0.99984 (1.9×) | 0.99978 (2.1×) | 0.99989 (1.6×) | 0.99984 (2.0×) | 0.99974 (1.6×) | 0.99977 (2.1×) |
| A5 | 0.99930 (1.8×) | 0.99986 (1.4×) | 0.99985 (1.4×) | 0.99982 (1.3×) | 0.99992 (1.3×) | 0.99988 (1.4×) | 0.99976 (1.4×) | 0.99982 (1.6×) |
| A6 | 0.99944 (1.2×) | 0.99988 (1.1×) | 0.99989 (1.0×) | 0.99988 (1.0×) | 0.99992 (1.0×) | 0.99988 (1.0×) | 0.99979 (1.0×) | 0.99986 (1.1×) |
| A7 | 0.99769 (3.5×) | 0.99952 (2.9×) | 0.99939 (2.9×) | 0.99930 (3.7×) | 0.99965 (3.3×) | 0.99942 (3.4×) | 0.99911 (2.4×) | 0.99895 (2.4×) |

### Offset length, all roles

The median over roles of |v_arm − r| / |v_A0 − r| per slot, averaged over layers: below 1 the arm's selection shortens the role's offset from r, above 1 lengthens it (the two subsets are in the JSON).

| arm | slot 0 | slot 1 | slot 2 | slot 3 | slot 4 | slot 5 | slot 6 | slot 7 |
|---|---|---|---|---|---|---|---|---|
| A0' | 0.9996 | 1.0001 | 0.9998 | 0.9998 | 1.0001 | 0.9998 | 0.9999 | 1.0002 |
| A1 | 1.0003 | 0.9994 | 0.9997 | 0.9998 | 0.9996 | 1.0000 | 1.0000 | 1.0000 |
| A2 | 1.0031 | 1.0002 | 0.9999 | 1.0001 | 0.9998 | 1.0001 | 1.0000 | 0.9999 |
| A3 | 1.0057 | 0.9998 | 1.0004 | 1.0002 | 0.9997 | 1.0001 | 1.0001 | 1.0002 |
| A4 | 1.0079 | 1.0011 | 1.0001 | 1.0004 | 0.9998 | 1.0005 | 1.0005 | 1.0013 |
| A5 | 1.0052 | 0.9996 | 0.9998 | 1.0001 | 0.9999 | 1.0002 | 1.0000 | 0.9999 |
| A6 | 1.0022 | 1.0001 | 1.0001 | 1.0003 | 1.0001 | 1.0003 | 0.9999 | 1.0002 |
| A7 | 1.0219 | 1.0011 | 1.0004 | 1.0028 | 1.0018 | 1.0009 | 1.0011 | 1.0017 |

### The roles that move most

Per arm, the 5 roles with the largest (1 − cos) relative to A0' 's, both averaged over layers and slots; every role, with its cosine, A0' 's and the offset length, is in the JSON (`moved_roles`).

| arm | roles |
|---|---|
| A1 | [assistant](../../../data/roles/instructions/assistant.json) 3.9×, [robot](../../../data/roles/instructions/robot.json) 2.4×, [psychologist](../../../data/roles/instructions/psychologist.json) 2.2×, [spirit](../../../data/roles/instructions/spirit.json) 1.6×, [merchant](../../../data/roles/instructions/merchant.json) 1.5× |
| A2 | [pirate](../../../data/roles/instructions/pirate.json) 2.5×, [ghost](../../../data/roles/instructions/ghost.json) 2.1×, [cyborg](../../../data/roles/instructions/cyborg.json) 2.0×, [merchant](../../../data/roles/instructions/merchant.json) 2.0×, [tree](../../../data/roles/instructions/tree.json) 1.6× |
| A3 | [realist](../../../data/roles/instructions/realist.json) 7.5×, [spirit](../../../data/roles/instructions/spirit.json) 3.0×, [cyborg](../../../data/roles/instructions/cyborg.json) 3.0×, [peacekeeper](../../../data/roles/instructions/peacekeeper.json) 2.1×, [organizer](../../../data/roles/instructions/organizer.json) 2.0× |
| A4 | [organizer](../../../data/roles/instructions/organizer.json) 5.1×, [realist](../../../data/roles/instructions/realist.json) 4.2×, [robot](../../../data/roles/instructions/robot.json) 3.7×, [psychologist](../../../data/roles/instructions/psychologist.json) 3.2×, [historian](../../../data/roles/instructions/historian.json) 2.8× |
| A5 | [realist](../../../data/roles/instructions/realist.json) 6.5×, [organizer](../../../data/roles/instructions/organizer.json) 4.5×, [peacekeeper](../../../data/roles/instructions/peacekeeper.json) 2.9×, [merchant](../../../data/roles/instructions/merchant.json) 2.5×, [contrarian](../../../data/roles/instructions/contrarian.json) 2.4× |
| A6 | [merchant](../../../data/roles/instructions/merchant.json) 2.3×, [cyborg](../../../data/roles/instructions/cyborg.json) 2.1×, [peacekeeper](../../../data/roles/instructions/peacekeeper.json) 2.0×, [psychologist](../../../data/roles/instructions/psychologist.json) 1.8×, [altruist](../../../data/roles/instructions/altruist.json) 1.7× |
| A7 | [assistant](../../../data/roles/instructions/assistant.json) 326.7×, [organizer](../../../data/roles/instructions/organizer.json) 33.2×, [realist](../../../data/roles/instructions/realist.json) 22.1×, [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) 17.9×, [interpreter](../../../data/roles/instructions/interpreter.json) 14.3× |

## Per role: responses scored 3 and status

| role | A0 | A0' | A1 | A2 | A3 | A4 | A5 | A6 | A7 |
|---|---|---|---|---|---|---|---|---|---|
| [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) | 251 | 244 | 263 | 220 | 263 | 231 | 274 | 235 | 77 |
| [assistant](../../../data/roles/instructions/assistant.json) | 452 | 453 | 452 | 453 | 452 | 451 | 449 | 454 | 183 |
| [cyborg](../../../data/roles/instructions/cyborg.json) | 474 | 476 | 476 | 470 | 464 | 464 | 468 | 466 | 477 |
| [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) | 432 | 428 | 428 | 429 | 422 | 418 | 424 | 428 | 421 |
| [robot](../../../data/roles/instructions/robot.json) | 233 | 248 | 240 | 245 | 197 | 146 | 210 | 224 | 192 |
| [minimalist](../../../data/roles/instructions/minimalist.json) | 268 | 262 | 263 | 255 | 264 | 224 | 267 | 268 | 202 |
| [peacekeeper](../../../data/roles/instructions/peacekeeper.json) | 214 | 209 | 234 | 207 | 214 | 157 | 215 | 245 | 107 |
| [realist](../../../data/roles/instructions/realist.json) | 357 | 349 | 337 | 314 | 247 | 207 | 238 | 405 | 88 |
| [validator](../../../data/roles/instructions/validator.json) | 232 | 252 | 240 | 240 | 174 | 129 | 161 | 259 | 47 |
| [emissary](../../../data/roles/instructions/emissary.json) | 227 | 234 | 235 | 229 | 232 | 228 | 233 | 216 | 231 |
| [pacifist](../../../data/roles/instructions/pacifist.json) | 311 | 331 | 332 | 304 | 331 | 306 | 358 | 311 | 271 |
| [perfectionist](../../../data/roles/instructions/perfectionist.json) | 127 | 141 | 140 | 131 | 129 | 108 | 128 | 156 | 95 |
| [interpreter](../../../data/roles/instructions/interpreter.json) | 259 | 272 | 256 | 275 | 220 | 190 | 243 | 265 | 97 |
| [altruist](../../../data/roles/instructions/altruist.json) | 236 | 235 | 229 | 223 | 303 | 245 | 304 | 236 | 172 |
| [soldier](../../../data/roles/instructions/soldier.json) | 393 | 401 | 412 | 394 | 407 | 382 | 416 | 393 | 375 |
| [biologist](../../../data/roles/instructions/biologist.json) | 434 | 428 | 432 | 432 | 428 | 428 | 445 | 420 | 412 |
| [visionary](../../../data/roles/instructions/visionary.json) | 352 | 361 | 365 | 345 | 352 | 292 | 336 | 352 | 242 |
| [psychologist](../../../data/roles/instructions/psychologist.json) | 437 | 430 | 425 | 432 | 429 | 358 | 442 | 403 | 319 |
| [historian](../../../data/roles/instructions/historian.json) | 434 | 423 | 423 | 417 | 419 | 379 | 418 | 424 | 325 |
| [contrarian](../../../data/roles/instructions/contrarian.json) | 366 | 366 | 366 | 360 | 326 | 273 | 317 | 377 | 175 |
| [organizer](../../../data/roles/instructions/organizer.json) | 431 | 440 | 446 | 444 | 395 | 322 | 380 | 434 | 208 |
| [merchant](../../../data/roles/instructions/merchant.json) | 333 | 336 | 334 | 325 | 339 | 324 | 339 | 334 | 328 |
| [familiar](../../../data/roles/instructions/familiar.json) | 436 | 435 | 440 | 434 | 449 | 431 | 449 | 431 | 444 |
| [alien](../../../data/roles/instructions/alien.json) | 499 | 499 | 499 | 500 | 499 | 499 | 499 | 499 | 499 |
| [ghost](../../../data/roles/instructions/ghost.json) | 485 | 487 | 483 | 483 | 486 | 482 | 486 | 484 | 486 |
| [guru](../../../data/roles/instructions/guru.json) | 482 | 481 | 483 | 483 | 484 | 466 | 482 | 484 | 484 |
| [oracle](../../../data/roles/instructions/oracle.json) | 479 | 473 | 478 | 477 | 480 | 474 | 479 | 481 | 489 |
| [pirate](../../../data/roles/instructions/pirate.json) | 498 | 498 | 496 | 499 | 500 | 497 | 500 | 498 | 499 |
| [spirit](../../../data/roles/instructions/spirit.json) | 491 | 495 | 495 | 489 | 493 | 485 | 492 | 491 | 495 |
| [tree](../../../data/roles/instructions/tree.json) | 401 | 400 | 402 | 407 | 406 | 404 | 401 | 397 | 400 |
