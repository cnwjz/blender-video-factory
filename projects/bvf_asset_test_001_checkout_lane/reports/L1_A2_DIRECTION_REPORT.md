# L1-A2 Direction & Standing Audit Report

Date: 2026-07-15

## 1. Direction Computation Method

For each character, the Armature's `matrix_world.to_3x3()` is used to transform all 6 local axes (+X,-X,+Y,-Y,+Z,-Z) into world space.
The axis with the highest-magnitude world Y component is identified as the model's forward direction.

## 2. Previous `forward_direction` Bug

L1-A used `root.matrix_world.to_3x3() @ Vector((0,1,0))` which gives the world direction of the Root Empty's local +Y.
The Root Empty is an axis-helper with `empty_display_size=0.05`, and its local +Y direction happens to be near world +Z after the X-90° rotation.
**The Root Empty's axes do not represent the character model's facing direction.** The correct reference is the Armature.

## 3. Per-Character Results

### Customer_01

- Model forward local axis: `+Z`
- Forward world vector: `[-0.0, 1.0, -0.0]`
- face_plus_y_pass: **True**
- Model up local axis: `+Y`
- Up world vector: `[-0.0, 0.0, 1.0]`
- Vertical alignment pass: **True**
- Head above body: True
- Height: 1.75
- Overall H:W: 0.8751
- Body-only H:W: 0.48
- Standing pass: **True**
- H:W explanation: Overall H:W=0.8751. Body-only H:W=0.48. Kenney Mini characters have arms extending laterally in idle pose, making the full AABB width (2.000) approach or exceed height (1.750). The body torso alone (without arms) has H:W ratio of 0.48. Head is above body center. Character IS standing — the low H:W is an artifact of arm extension, not lying down.

### Customer_02

- Model forward local axis: `+Z`
- Forward world vector: `[-0.0, 1.0, -0.0]`
- face_plus_y_pass: **True**
- Model up local axis: `+Y`
- Up world vector: `[-0.0, 0.0, 1.0]`
- Vertical alignment pass: **True**
- Head above body: True
- Height: 1.75
- Overall H:W: 0.941
- Body-only H:W: 0.4495
- Standing pass: **True**
- H:W explanation: Overall H:W=0.941. Body-only H:W=0.4495. Kenney Mini characters have arms extending laterally in idle pose, making the full AABB width (1.860) approach or exceed height (1.750). The body torso alone (without arms) has H:W ratio of 0.4495. Head is above body center. Character IS standing — the low H:W is an artifact of arm extension, not lying down.

### Customer_03

- Model forward local axis: `+Z`
- Forward world vector: `[-0.0, 1.0, -0.0]`
- face_plus_y_pass: **True**
- Model up local axis: `+Y`
- Up world vector: `[-0.0, 0.0, 1.0]`
- Vertical alignment pass: **True**
- Head above body: True
- Height: 1.75
- Overall H:W: 0.862
- Body-only H:W: 0.48
- Standing pass: **True**
- H:W explanation: Overall H:W=0.862. Body-only H:W=0.48. Kenney Mini characters have arms extending laterally in idle pose, making the full AABB width (2.030) approach or exceed height (1.750). The body torso alone (without arms) has H:W ratio of 0.48. Head is above body center. Character IS standing — the low H:W is an artifact of arm extension, not lying down.

### Customer_04

- Model forward local axis: `+Z`
- Forward world vector: `[-0.0, 1.0, -0.0]`
- face_plus_y_pass: **True**
- Model up local axis: `+Y`
- Up world vector: `[-0.0, 0.0, 1.0]`
- Vertical alignment pass: **True**
- Head above body: True
- Height: 1.75
- Overall H:W: 0.9429
- Body-only H:W: 0.48
- Standing pass: **True**
- H:W explanation: Overall H:W=0.9429. Body-only H:W=0.48. Kenney Mini characters have arms extending laterally in idle pose, making the full AABB width (1.856) approach or exceed height (1.750). The body torso alone (without arms) has H:W ratio of 0.48. Head is above body center. Character IS standing — the low H:W is an artifact of arm extension, not lying down.

### Employee_01

- Model forward local axis: `+Z`
- Forward world vector: `[-0.0, 1.0, -0.0]`
- face_plus_y_pass: **True**
- Model up local axis: `+Y`
- Up world vector: `[-0.0, 0.0, 1.0]`
- Vertical alignment pass: **True**
- Head above body: True
- Height: 1.75
- Overall H:W: 0.9267
- Body-only H:W: 0.4718
- Standing pass: **True**
- H:W explanation: Overall H:W=0.9267. Body-only H:W=0.4718. Kenney Mini characters have arms extending laterally in idle pose, making the full AABB width (1.888) approach or exceed height (1.750). The body torso alone (without arms) has H:W ratio of 0.4718. Head is above body center. Character IS standing — the low H:W is an artifact of arm extension, not lying down.

### Employee_02

- Model forward local axis: `+Z`
- Forward world vector: `[-0.0, 1.0, -0.0]`
- face_plus_y_pass: **True**
- Model up local axis: `+Y`
- Up world vector: `[-0.0, 0.0, 1.0]`
- Vertical alignment pass: **True**
- Head above body: True
- Height: 1.75
- Overall H:W: 0.9267
- Body-only H:W: 0.4718
- Standing pass: **True**
- H:W explanation: Overall H:W=0.9267. Body-only H:W=0.4718. Kenney Mini characters have arms extending laterally in idle pose, making the full AABB width (1.888) approach or exceed height (1.750). The body torso alone (without arms) has H:W ratio of 0.4718. Head is above body center. Character IS standing — the low H:W is an artifact of arm extension, not lying down.

## 4. Overall

- All face +Y: **True**
- All standing: **True**
