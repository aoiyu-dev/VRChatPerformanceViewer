#  Copyright (C) 2025 aoiyu_ <aoicsharp@outlook.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#  Description: Shows the performance of a VRChat Avatar directly in the
#  3D Viewport.

bl_info = {
    "name": "VRChat Performance Viewer",
    "author": "aoiyu_",
    "version": (1, 1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > VRChat",
    "description": "Displays VRChat avatar performance stats.",
    "category": "3D View",
}

import bpy
import os
import bpy.utils.previews
from enum import Enum

# Constant limitation values just in case they are altered.
VRC_ANDROID_TRIS_EXCELLENT = 7500
VRC_ANDROID_TRIS_GOOD = 10000
VRC_ANDROID_TRIS_MEDIUM = 15000
VRC_ANDROID_TRIS_POOR = 20000

VRC_PC_TRIS_EXCELLENT = 32000
VRC_PC_TRIS_GOOD = 70000

VRC_ANDROID_SKINNED_MESH_EXCELLENT = 1
VRC_ANDROID_SKINNED_MESH_MEDIUM = 2

VRC_PC_SKINNED_MESH_EXCELLENT = 1
VRC_PC_SKINNED_MESH_GOOD = 2
VRC_PC_SKINNED_MESH_MEDIUM = 8
VRC_PC_SKINNED_MESH_POOR = 16

VRC_ANDROID_BASIC_MESH_EXCELLENT = 1
VRC_ANDROID_BASIC_MESH_MEDIUM = 2

VRC_PC_BASIC_MESH_EXCELLENT = 4
VRC_PC_BASIC_MESH_GOOD = 8
VRC_PC_BASIC_MESH_MEDIUM = 16
VRC_PC_BASIC_MESH_POOR = 24

VRC_ANDROID_MATERIALS_EXCELLENT = 1
VRC_ANDROID_MATERIALS_MEDIUM = 2
VRC_ANDROID_MATERIALS_POOR = 4

VRC_PC_MATERIALS_EXCELLENT = 4
VRC_PC_MATERIALS_GOOD = 8
VRC_PC_MATERIALS_MEDIUM = 16
VRC_PC_MATERIALS_POOR = 32

VRC_ANDROID_BONES_EXCELLENT = 75
VRC_ANDROID_BONES_GOOD = 90
VRC_ANDROID_BONES_MEDIUM = 150

VRC_PC_BONES_EXCELLENT = 75
VRC_PC_BONES_GOOD = 150
VRC_PC_BONES_MEDIUM = 256
VRC_PC_BONES_POOR = 400

class ValueType(Enum):
    # Enum for the types we poll for readability

    TRIS = "Tris"
    SKINNED_MESH = "Skinned Mesh"
    BASIC_MESH = "Basic Mesh"
    MATERIALS = "Materials"
    BONES = "Bones"

class MeasuredStats:
    total_tri_count = 0
    total_mat_count = 0
    bone_count = 0
    skinned_mesh = 0
    basic_mesh = 0

class VRCGlobalFunctions:

    # Draw the UI with the numbers right aligned
    @staticmethod
    def draw_labeled_row(layout, label, value, value_type, is_mobile=False, factor=0.4, selected_value=None):
        max_value = ValueProvider.get_value(value_type, value, is_mobile)
        icon = IconProvider.get_icon(value_type, value, is_mobile)

        row = layout.row(align=True)
        split = row.split(factor=factor)

        left = split.row(align=True)
        left.label(text=label, icon_value=icon)

        right = split.row(align=True)
        right.alignment = 'RIGHT'

        # Display selected values if selected or not
        if selected_value is not None:
            right.label(text=f"{value}/{max_value} ({selected_value})")
        else:
            right.label(text=f"{value}/{max_value}")

    @staticmethod
    def walk_children(obj, measured_stats, is_collection):
        VRCGlobalFunctions.get_stats_for_object(obj, measured_stats)
        if is_collection:
            for child in obj.objects:
                VRCGlobalFunctions.get_stats_for_object(child, measured_stats)
        else:
            for child in obj.children_recursive:
                VRCGlobalFunctions.get_stats_for_object(child, measured_stats)

    @staticmethod
    def get_stats_for_object(obj, measured_stats):
        if isinstance(obj, bpy.types.Collection):
            # it's a collection, there are no stats to calculate for collections,
            # and they don't have the field "type", so exit early
            return
        elif obj.type == "MESH":
            tri_count, mat_count = VRCGlobalFunctions.get_materials_and_tris_from_mesh(obj)
            measured_stats.total_tri_count += tri_count
            measured_stats.total_mat_count += mat_count
            if any(mod.type == "ARMATURE" for mod in obj.modifiers) or \
        (obj.data.shape_keys is not None and len(obj.data.shape_keys.key_blocks) > 1):
                measured_stats.skinned_mesh += 1
            else:
                measured_stats.basic_mesh += 1
        elif obj.type == "ARMATURE":
            measured_stats.bone_count += len(obj.data.bones)

    @staticmethod
    def get_selected():
        if len(bpy.context.selected_objects) == 0 and bpy.context.view_layer.active_layer_collection is not None:
            print("Collection selected.")
            return bpy.context.view_layer.active_layer_collection.collection, True
        elif len(bpy.context.selected_objects) > 0:
            print("Object selected.", bpy.context.object)
            return bpy.context.object, False
        else:
            print("No object selected.")
            return None, None

    @staticmethod
    def get_materials_and_tris_from_mesh(mesh):
        # Count of tris and mats on the selected mesh
        tri_count = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
        mat_count = len(mesh.material_slots)

        return tri_count, mat_count

    @staticmethod
    def get_icon_and_name_for_selection():

        # Get the currently selected object
        obj, is_collection = VRCGlobalFunctions.get_selected()

        if obj:
            # Retrieve the object's name
            # object_name = obj.name

            # Retrieve the icon corresponding to the object's type
            # icon = bpy.types.UILayout.bl_rna.functions['prop'].parameters['icon'].enum_items.get(obj.type).icon
            # icon = bpy.types.UILayout.icon(bpy.context.object)
            object_name = ""
            icon = ""

            if is_collection:
                object_name = obj.name
                icon = "OUTLINER_COLLECTION"
            elif obj.type == "ARMATURE":
                object_name = obj.name
                icon = "OUTLINER_OB_ARMATURE"
            elif obj.type == "MESH":
                object_name = obj.name
                icon = "MESH_CUBE"
            elif obj.type == "EMPTY":
                object_name = obj.name
                icon = "OUTLINER_OB_EMPTY"

            print(f"Object Name: {object_name}")
            print(f"Object Icon: {icon}")
            return icon, object_name
        else:
            print("No object selected.")
            return None, None

    @staticmethod
    def draw_perf_labels(
            layout,
            measured_stats: MeasuredStats,
            is_mobile=False):

        icon, object_name = VRCGlobalFunctions.get_icon_and_name_for_selection()
        # Drawing UI
        layout.label(text=f"{object_name}", icon=icon)
        if measured_stats.skinned_mesh > 0:
            VRCGlobalFunctions.draw_labeled_row(layout, "Skinned Mesh:", measured_stats.skinned_mesh, ValueType.SKINNED_MESH, is_mobile, 0.8)
        if measured_stats.basic_mesh > 0:
            VRCGlobalFunctions.draw_labeled_row(layout, "Basic Mesh:", measured_stats.basic_mesh, ValueType.BASIC_MESH, is_mobile, 0.8)
        if measured_stats.total_tri_count > 0:
            VRCGlobalFunctions.draw_labeled_row(layout, "Tris:", measured_stats.total_tri_count, ValueType.TRIS, is_mobile, 0.3, measured_stats.total_tri_count)
        if measured_stats.total_mat_count > 0:
            VRCGlobalFunctions.draw_labeled_row(layout, "Materials:", measured_stats.total_mat_count, ValueType.MATERIALS, is_mobile, 0.6, measured_stats.total_mat_count)
        if measured_stats.bone_count > 0:
            VRCGlobalFunctions.draw_labeled_row(layout, "Bones:", measured_stats.bone_count, ValueType.BONES, is_mobile, 0.5)

    @staticmethod
    def determine_draw_path(layout, is_mobile):
        obj, is_collection = VRCGlobalFunctions.get_selected()
        global custom_icons

        measured_stats = MeasuredStats()

        if is_collection:
            VRCGlobalFunctions.walk_children(obj, measured_stats, is_collection)
            VRCGlobalFunctions.draw_perf_labels(layout, measured_stats, is_mobile)
            return
        if obj.parent is not None and obj.parent.type == "ARMATURE":
            VRCGlobalFunctions.walk_children(obj.parent, measured_stats, is_collection)
            VRCGlobalFunctions.draw_perf_labels(layout, measured_stats, is_mobile)
            return
        else:
            VRCGlobalFunctions.walk_children(obj, measured_stats, is_collection)
            VRCGlobalFunctions.draw_perf_labels(layout, measured_stats, is_mobile)
            return


class VRCRank(bpy.types.Panel):
    # Panel for PC Rank

    bl_label = "VRChat Avatar Rank (PC)"
    bl_idname = "PT_VRCAR"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRChat"
    
    def draw(self, context):
        VRCGlobalFunctions.determine_draw_path(self.layout, False)
        return


class VRCRankMobile(bpy.types.Panel):
    # Panel for Mobile Rank

    bl_label = "VRChat Avatar Rank (Mobile)"
    bl_idname = "PT_VRCARQ"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRChat"

    def draw(self, context):
        VRCGlobalFunctions.determine_draw_path(self.layout, True)
        return

class IconProvider:
    # Handles icon selection based on ValueType.

    @staticmethod
    def get_icon(value_type: ValueType, count: int, mobile: bool) -> int:
        # Returns an icon_value for Blender UI based on the given ValueType.
        method_name = f"get_{value_type.name.lower()}_icon"
        method = getattr(IconProvider, method_name, IconProvider.get_default_icon)
        return method(count, mobile)

    @staticmethod
    def get_tris_icon(count: int, mobile: bool) -> int:
        global custom_icons
        if mobile:
            if count <= VRC_ANDROID_TRIS_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_ANDROID_TRIS_GOOD:
                return custom_icons["vrc_good"].icon_id
            elif count <= VRC_ANDROID_TRIS_MEDIUM:
                return custom_icons["vrc_medium"].icon_id
            elif count <= VRC_ANDROID_TRIS_POOR:
                return custom_icons["vrc_poor"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id
        else:
            if count <= VRC_PC_TRIS_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_PC_TRIS_GOOD:
                return custom_icons["vrc_good"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id

    @staticmethod
    def get_skinned_mesh_icon(count: int, mobile: bool):
        global custom_icons
        if mobile:
            if count <= VRC_ANDROID_SKINNED_MESH_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_ANDROID_SKINNED_MESH_MEDIUM:
                return custom_icons["vrc_medium"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id
        else:
            if count <= VRC_PC_SKINNED_MESH_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_PC_SKINNED_MESH_GOOD:
                return custom_icons["vrc_good"].icon_id
            elif count <= VRC_PC_SKINNED_MESH_MEDIUM:
                return custom_icons["vrc_medium"].icon_id
            elif count <= VRC_PC_SKINNED_MESH_POOR:
                return custom_icons["vrc_poor"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id

    @staticmethod
    def get_basic_mesh_icon(count: int, mobile: bool):
        global custom_icons
        if mobile:
            if count <= VRC_ANDROID_BASIC_MESH_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_ANDROID_BASIC_MESH_MEDIUM:
                return custom_icons["vrc_medium"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id
        else:
            if count <= VRC_PC_BASIC_MESH_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_PC_BASIC_MESH_GOOD:
                return custom_icons["vrc_good"].icon_id
            elif count <= VRC_PC_BASIC_MESH_MEDIUM:
                return custom_icons["vrc_medium"].icon_id
            elif count <= VRC_PC_BASIC_MESH_POOR:
                return custom_icons["vrc_poor"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id

    @staticmethod
    def get_materials_icon(count: int, mobile: bool):
        global custom_icons
        if mobile:
            if count <= VRC_ANDROID_MATERIALS_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_ANDROID_MATERIALS_MEDIUM:
                return custom_icons["vrc_medium"].icon_id
            elif count <= VRC_ANDROID_MATERIALS_POOR:
                return custom_icons["vrc_poor"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id
        else:
            if count <= VRC_PC_MATERIALS_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_PC_MATERIALS_GOOD:
                return custom_icons["vrc_good"].icon_id
            elif count <= VRC_PC_MATERIALS_MEDIUM:
                return custom_icons["vrc_medium"].icon_id
            elif count <= VRC_PC_MATERIALS_POOR:
                return custom_icons["vrc_poor"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id

    @staticmethod
    def get_bones_icon(count: int, mobile: bool):
        global custom_icons
        if mobile:
            if count <= VRC_ANDROID_BONES_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_ANDROID_BONES_GOOD:
                return custom_icons["vrc_good"].icon_id
            elif count <= VRC_ANDROID_BONES_MEDIUM:
                return custom_icons["vrc_medium"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id
        else:
            if count <= VRC_PC_BONES_EXCELLENT:
                return custom_icons["vrc_excellent"].icon_id
            elif count <= VRC_PC_BONES_GOOD:
                return custom_icons["vrc_good"].icon_id
            elif count <= VRC_PC_BONES_MEDIUM:
                return custom_icons["vrc_medium"].icon_id
            elif count <= VRC_PC_BONES_POOR:
                return custom_icons["vrc_poor"].icon_id
            else:
                return custom_icons["vrc_verypoor"].icon_id

    @staticmethod
    def get_default_icon(count: int, mobile: bool):
        global custom_icons
        return custom_icons["vrc_excellent"].icon_id

class ValueProvider:
    # Handles max value selection based on ValueType.

    @staticmethod
    def get_value(value_type: ValueType, count: int, mobile: bool) -> int:
        # Returns the next step-up in value based on the given ValueType.
        method_name = f"get_{value_type.name.lower()}_value"
        method = getattr(ValueProvider, method_name, ValueProvider.get_default_value)
        return method(count, mobile)

    @staticmethod
    def get_tris_value(count: int, mobile: bool) -> int:
        if mobile:
            if count <= VRC_ANDROID_TRIS_EXCELLENT:
                return VRC_ANDROID_TRIS_EXCELLENT
            elif count <= VRC_ANDROID_TRIS_GOOD:
                return VRC_ANDROID_TRIS_GOOD
            elif count <= VRC_ANDROID_TRIS_MEDIUM:
                return VRC_ANDROID_TRIS_MEDIUM
            else:
                return VRC_ANDROID_TRIS_POOR
        else:
            if count <= VRC_PC_TRIS_EXCELLENT:
                return VRC_PC_TRIS_EXCELLENT
            else:
                return VRC_PC_TRIS_GOOD

    @staticmethod
    def get_skinned_mesh_value(count: int, mobile: bool) -> int:
        if mobile:
            if count <= VRC_ANDROID_SKINNED_MESH_EXCELLENT:
                return VRC_ANDROID_SKINNED_MESH_EXCELLENT
            else:
                return VRC_ANDROID_SKINNED_MESH_MEDIUM
        else:
            if count <= VRC_PC_SKINNED_MESH_EXCELLENT:
                return VRC_PC_SKINNED_MESH_EXCELLENT
            elif count <= VRC_PC_SKINNED_MESH_GOOD:
                return VRC_PC_SKINNED_MESH_GOOD
            elif count <= VRC_PC_SKINNED_MESH_MEDIUM:
                return VRC_PC_SKINNED_MESH_MEDIUM
            else:
                return VRC_PC_SKINNED_MESH_POOR

    @staticmethod
    def get_basic_mesh_value(count: int, mobile: bool) -> int:
        if mobile:
            if count <= VRC_ANDROID_BASIC_MESH_EXCELLENT:
                return VRC_ANDROID_BASIC_MESH_EXCELLENT
            else:
                return VRC_ANDROID_BASIC_MESH_MEDIUM
        else:
            if count <= VRC_PC_BASIC_MESH_EXCELLENT:
                return VRC_PC_BASIC_MESH_EXCELLENT
            elif count <= VRC_PC_BASIC_MESH_GOOD:
                return VRC_PC_BASIC_MESH_GOOD
            elif count <= VRC_PC_BASIC_MESH_MEDIUM:
                return VRC_PC_BASIC_MESH_MEDIUM
            else:
                return VRC_PC_BASIC_MESH_POOR

    @staticmethod
    def get_materials_value(count: int, mobile: bool) -> int:
        if mobile:
            if count <= VRC_ANDROID_MATERIALS_EXCELLENT:
                return VRC_ANDROID_MATERIALS_EXCELLENT
            elif count <= VRC_ANDROID_MATERIALS_MEDIUM:
                return VRC_ANDROID_MATERIALS_MEDIUM
            else:
                return VRC_ANDROID_MATERIALS_POOR
        else:
            if count <= VRC_PC_MATERIALS_EXCELLENT:
                return VRC_PC_MATERIALS_EXCELLENT
            elif count <= VRC_PC_MATERIALS_GOOD:
                return VRC_PC_MATERIALS_GOOD
            elif count <= VRC_PC_MATERIALS_MEDIUM:
                return VRC_PC_MATERIALS_MEDIUM
            else:
                return VRC_PC_MATERIALS_POOR

    @staticmethod
    def get_bones_value(count: int, mobile: bool) -> int:
        if mobile:
            if count <= VRC_ANDROID_BONES_EXCELLENT:
                return VRC_ANDROID_BONES_EXCELLENT
            elif count <= VRC_ANDROID_BONES_GOOD:
                return VRC_ANDROID_BONES_GOOD
            else:
                return VRC_ANDROID_BONES_MEDIUM
        else:
            if count <= VRC_PC_BONES_EXCELLENT:
                return VRC_PC_BONES_EXCELLENT
            elif count <= VRC_PC_BONES_GOOD:
                return VRC_PC_BONES_GOOD
            elif count <= VRC_PC_BONES_MEDIUM:
                return VRC_PC_BONES_MEDIUM
            else:
                return VRC_PC_BONES_POOR

    @staticmethod
    def get_default_value(count: int, mobile: bool) -> int:
        return 0

custom_icons = None
        
def register():
    global custom_icons
    custom_icons = bpy.utils.previews.new()

    # Get the path of the custom icons.
    addon_path = os.path.dirname(__file__)
    icons_dir = os.path.join(addon_path, "icons")

    # Load the custom icons.
    custom_icons.load("vrc_excellent", os.path.join(icons_dir, "excellent.png"), "IMAGE")
    custom_icons.load("vrc_good", os.path.join(icons_dir, "good.png"), "IMAGE")
    custom_icons.load("vrc_medium", os.path.join(icons_dir, "medium.png"), "IMAGE")
    custom_icons.load("vrc_poor", os.path.join(icons_dir, "poor.png"), "IMAGE")
    custom_icons.load("vrc_verypoor", os.path.join(icons_dir, "verypoor.png"), "IMAGE")

    bpy.utils.register_class(VRCRank)
    bpy.utils.register_class(VRCRankMobile)


def unregister():
    global custom_icons
    bpy.utils.previews.remove(custom_icons)
    bpy.utils.unregister_class(VRCRank)
    bpy.utils.unregister_class(VRCRankMobile)


if __name__ == "__main__":
    register()