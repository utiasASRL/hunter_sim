import bpy
import sys

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import OBJ (adjust the path if needed)
bpy.ops.import_scene.obj(filepath="model.obj")

# Optional: Apply transforms, center, etc.
for obj in bpy.context.selected_objects:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

# Export as DAE
bpy.ops.wm.collada_export(filepath="model.dae")

