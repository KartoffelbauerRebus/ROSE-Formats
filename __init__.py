import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
# noinspection PyUnresolvedReferences
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper, ExportHelper
from .zmd_export import save_zmd_skeleton
from .zmd_import import load_zmd_skeleton
from .zmo_import import load_zmo_animation
from .zms_import import load_zms_mesh

bl_info = {
    "name": "ROSE Online Formats",
    "blender": (3, 2, 0),
    "category": "Import-Export",
}


class ImportZMD(Operator, ImportHelper):
    """Import a ZMD file to generate a skeleton."""
    bl_idname = "rose_formats.zmd_import"
    bl_label = "Import ZMD"

    filename_ext = ".zmd"

    filter_glob: StringProperty(
        default="*.zmd",
        options={'HIDDEN'},
        maxlen=255,
    )

    load_animations: BoolProperty(
        name="Load Animations",
        description="Load all ZMO animations from the same directory.",
        default=False,
    )

    add_leg_ik: BoolProperty(
        name="Add Leg IK",
        description="Add and setup Inverse Kinematic controls to the legs if possible.",
        default=False,
    )

    add_arm_ik: BoolProperty(
        name="Add Arm IK",
        description="Add and setup Inverse Kinematic controls to the arms if possible.",
        default=False,
    )

    def execute(self, context):
        return load_zmd_skeleton(context, self.filepath, self.load_animations, self.add_leg_ik, self.add_arm_ik)


class ImportZMO(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "rose_formats.zmo_import"
    bl_label = "Import ZMO"

    filename_ext = ".zmo"

    filter_glob: StringProperty(
        default="*.zmo",
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        return load_zmo_animation(context, self.filepath)


class ImportZMS(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "rose_formats.zms_import"
    bl_label = "Import ZMS"

    filename_ext = ".zms"

    filter_glob: StringProperty(
        default="*.zms",
        options={'HIDDEN'},
        maxlen=255,
    )

    use_setting: BoolProperty(
        name="Load Texture",
        description="Load all DDS textures with the same name from the same directory.",
        default=False,
    )

    def execute(self, context):
        return load_zms_mesh(context, self.filepath, self.use_setting)


class ExportZMD(Operator, ExportHelper):
    """Export a skeleton to a ZMD file."""
    bl_idname = "rose_formats.zmd_export"
    bl_label = "Export ZMD"

    filename_ext = ".zmd"

    filter_glob: StringProperty(
        default="*.zmd",
        options={'HIDDEN'},
        maxlen=255,
    )

    format_code: EnumProperty(
        name="Format Version",
        description="Choose the between the formatting standards.",
        items=(
            ('3', "ZMD0003", "Used for character skeletons, dummies have rotation data."),
            ('2', "ZMD0002", "Used for character skeletons, dummies do not have rotation data."),
        ),
        default='3',
    )

    def execute(self, context):
        return save_zmd_skeleton(context, self.filepath, self.format_code)


def menu_func_import(self, context):
    self.layout.operator(ImportZMD.bl_idname, text="ZMD (.zmd)")
    self.layout.operator(ImportZMO.bl_idname, text="ZMO (.zmo)")
    self.layout.operator(ImportZMS.bl_idname, text="ZMS (.zms)")


def menu_func_export(self, context):
    self.layout.operator(ExportZMD.bl_idname, text="ZMD (.zmd")


def register():
    bpy.utils.register_class(ImportZMD)
    bpy.utils.register_class(ImportZMO)
    bpy.utils.register_class(ImportZMS)
    bpy.utils.register_class(ExportZMD)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ImportZMD)
    bpy.utils.unregister_class(ImportZMO)
    bpy.utils.unregister_class(ImportZMS)
    bpy.utils.unregister_class(ExportZMD)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
