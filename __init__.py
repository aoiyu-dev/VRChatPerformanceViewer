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

class VRCRank(bpy.types.Panel):
    # Panel for PC Rank

    bl_label = "VRChat Avatar Rank (PC)"
    bl_idname = "PT_VRCAR"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "aoiyu_"
    
    def draw(self, context):
        layout = self.layout

        # Draw the UI with the numbers right aligned
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

        selected_objects = context.selected_objects

        if len(selected_objects) > 1:
            current_parent = None
            sel_tri_count = 0
            sel_mat_count = 0
            total_tri_count = 0
            total_mat_count = 0
            skinned_mesh = 0
            basic_mesh = 0
            bone_count = 0

            for obj in selected_objects:
                if obj.type != 'MESH':
                    continue
                if obj.parent is None or obj.parent.type != 'ARMATURE':
                    row = layout.row()
                    row.label(text="The current selection is not supported.")
                    return
                if current_parent is None:
                    current_parent = obj.parent
                    total_tri_count = sum(
                        sum(len(p.vertices) - 2 for p in child.data.polygons) for child in obj.parent.children if
                        child.type == 'MESH')
                    total_mat_count = sum(
                        len(child.material_slots) for child in obj.parent.children if child.type == "MESH")
                    for child in obj.parent.children:
                        if child.type == "MESH":
                            if any(mod.type == "ARMATURE" for mod in child.modifiers):
                                skinned_mesh += 1
                            else:
                                basic_mesh += 1
                if current_parent != obj.parent:
                    row = layout.row()
                    row.label(text="Multiple parent selection is not supported.")
                    return
                sel_tri_count += sum(len(p.vertices) - 2 for p in obj.data.polygons)
                sel_mat_count += len(obj.material_slots)
                bone_count = len(obj.parent.data.bones)
            if current_parent is None:
                row = layout.row()
                row.label(text="The current selection is not supported.")
                return
            layout.label(text=f"{current_parent.name} (Multi Select Mode)", icon="OUTLINER_OB_ARMATURE")
            draw_labeled_row(layout, "Skinned Mesh:", skinned_mesh, ValueType.SKINNED_MESH, False, 0.8)
            if basic_mesh > 0:
                draw_labeled_row(layout, "Basic Mesh:", basic_mesh, ValueType.BASIC_MESH, False, 0.8)
            draw_labeled_row(layout, "Tris:", total_tri_count, ValueType.TRIS, False, 0.3, sel_tri_count)
            draw_labeled_row(layout, "Materials:", total_mat_count, ValueType.MATERIALS, False, 0.6, sel_mat_count)
            draw_labeled_row(layout, "Bones:", bone_count, ValueType.BONES, False, 0.5)
            return

        obj = context.object
        global custom_icons
        
        row = layout.row()
        if obj is None or obj.type != "MESH" and obj.type != "ARMATURE":
            row.label(text="Currently Unavailable")
            return
        
        parent = obj.parent
        if parent is not None and parent.type == "ARMATURE":
            # Count of tris and mats on the entire armature
            total_tri_count = sum(sum(len(p.vertices) - 2 for p in child.data.polygons) for child in parent.children if child.type == 'MESH')
            total_mat_count = sum(len(child.material_slots) for child in parent.children if child.type == "MESH")
            
            # Get the number of bones
            bone_count = len(parent.data.bones)
            
            # Skinned Mesh or Basic Mesh
            skinned_mesh = 0
            basic_mesh = 0
            for child in parent.children:
                if child.type == "MESH":
                    if any(mod.type == "ARMATURE" for mod in child.modifiers):
                        skinned_mesh += 1
                    else:
                        basic_mesh += 1
            
            # Count of tris and mats on the selected mesh
            tri_count = sum(len(p.vertices) - 2 for p in obj.data.polygons)
            mat_count = len(obj.material_slots)
            
            # Drawing UI
            layout.label(text=f"{parent.name}", icon="OUTLINER_OB_ARMATURE")
            draw_labeled_row(layout, "Skinned Mesh:", skinned_mesh, ValueType.SKINNED_MESH, False, 0.8)
            if basic_mesh > 0:
                draw_labeled_row(layout, "Basic Mesh:", basic_mesh, ValueType.BASIC_MESH, False, 0.8)
            draw_labeled_row(layout, "Tris:", total_tri_count, ValueType.TRIS, False, 0.3, tri_count)
            draw_labeled_row(layout, "Materials:", total_mat_count, ValueType.MATERIALS, False, 0.6, mat_count)
            draw_labeled_row(layout, "Bones:", bone_count, ValueType.BONES, False, 0.5)
            return
        elif obj.type == "ARMATURE":
            # Count of tris and mats on the entire armature
            total_tri_count = sum(sum(len(p.vertices) - 2 for p in child.data.polygons) for child in obj.children if child.type == 'MESH')
            total_mat_count = sum(len(child.material_slots) for child in obj.children if child.type == "MESH")
            
            # Get the number of bones
            bone_count = len(obj.data.bones)
            
            # Skinned Mesh or Basic Mesh
            skinned_mesh = 0
            basic_mesh = 0
            for child in obj.children:
                if child.type == "MESH":
                    if any(mod.type == "ARMATURE" for mod in child.modifiers):
                        skinned_mesh += 1
                    else:
                        basic_mesh += 1
            
            # Drawing UI
            layout.label(text=f"{obj.name}", icon="OUTLINER_OB_ARMATURE")
            draw_labeled_row(layout, "Skinned Mesh:", skinned_mesh, ValueType.SKINNED_MESH, False, 0.8)
            if basic_mesh > 0:
                draw_labeled_row(layout, "Basic Mesh:", basic_mesh, ValueType.BASIC_MESH, False, 0.8)
            draw_labeled_row(layout, "Tris:", total_tri_count, ValueType.TRIS, False)
            draw_labeled_row(layout, "Materials:", total_mat_count, ValueType.MATERIALS, False, 0.6)
            draw_labeled_row(layout, "Bones:", bone_count, ValueType.BONES, False, 0.5)
            return
        else:
            # Count of tris and mats
            tri_count = sum(len(p.vertices) - 2 for p in obj.data.polygons)
            mat_count = len(obj.material_slots)
            
            # Drawing UI
            layout.label(text=f"{obj.name}", icon="MESH_CUBE")
            draw_labeled_row(layout, "Tris:", tri_count, ValueType.TRIS, False)
            draw_labeled_row(layout, "Materials:", mat_count, ValueType.MATERIALS, False, 0.6)
            return


class VRCRankMobile(bpy.types.Panel):
    # Panel for Mobile Rank

    bl_label = "VRChat Avatar Rank (Mobile)"
    bl_idname = "PT_VRCARQ"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "aoiyu_"

    def draw(self, context):
        layout = self.layout

        # Draw the UI with the numbers right aligned
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

        selected_objects = context.selected_objects

        if len(selected_objects) > 1:
            current_parent = None
            sel_tri_count = 0
            sel_mat_count = 0
            total_tri_count = 0
            total_mat_count = 0
            skinned_mesh = 0
            basic_mesh = 0
            bone_count = 0

            for obj in selected_objects:
                if obj.type != 'MESH':
                    continue
                if obj.parent is None or obj.parent.type != 'ARMATURE':
                    row = layout.row()
                    row.label(text="The current selection is not supported.")
                    return
                if current_parent is None:
                    current_parent = obj.parent
                    total_tri_count = sum(
                        sum(len(p.vertices) - 2 for p in child.data.polygons) for child in obj.parent.children if
                        child.type == 'MESH')
                    total_mat_count = sum(
                        len(child.material_slots) for child in obj.parent.children if child.type == "MESH")
                    for child in obj.parent.children:
                        if child.type == "MESH":
                            if any(mod.type == "ARMATURE" for mod in child.modifiers):
                                skinned_mesh += 1
                            else:
                                basic_mesh += 1
                if current_parent != obj.parent:
                    row = layout.row()
                    row.label(text="Multiple parent selection is not supported.")
                    return
                sel_tri_count += sum(len(p.vertices) - 2 for p in obj.data.polygons)
                sel_mat_count += len(obj.material_slots)
                bone_count = len(obj.parent.data.bones)
            if current_parent is None:
                row = layout.row()
                row.label(text="The current selection is not supported.")
                return
            layout.label(text=f"{current_parent.name} (Multi Select Mode)", icon="OUTLINER_OB_ARMATURE")
            draw_labeled_row(layout, "Skinned Mesh:", skinned_mesh, ValueType.SKINNED_MESH, True, 0.8)
            if basic_mesh > 0:
                draw_labeled_row(layout, "Basic Mesh:", basic_mesh, ValueType.BASIC_MESH, True, 0.8)
            draw_labeled_row(layout, "Tris:", total_tri_count, ValueType.TRIS, True, 0.3, sel_tri_count)
            draw_labeled_row(layout, "Materials:", total_mat_count, ValueType.MATERIALS, True, 0.6, sel_mat_count)
            draw_labeled_row(layout, "Bones:", bone_count, ValueType.BONES, True, 0.5)
            return

        obj = context.object
        global custom_icons

        row = layout.row()
        if obj is None or obj.type != "MESH" and obj.type != "ARMATURE":
            row.label(text="The current selection is not supported.")
            return

        parent = obj.parent
        if parent is not None and parent.type == "ARMATURE":
            # Count of tris and mats on the entire armature
            total_tri_count = sum(sum(len(p.vertices) - 2 for p in child.data.polygons) for child in parent.children if
                                  child.type == 'MESH')
            total_mat_count = sum(len(child.material_slots) for child in parent.children if child.type == "MESH")

            # Get the number of bones
            bone_count = len(parent.data.bones)

            # Skinned Mesh or Basic Mesh
            skinned_mesh = 0
            basic_mesh = 0
            for child in parent.children:
                if child.type == "MESH":
                    if any(mod.type == "ARMATURE" for mod in child.modifiers):
                        skinned_mesh += 1
                    else:
                        basic_mesh += 1

            # Count of tris and mats on the selected mesh
            tri_count = sum(len(p.vertices) - 2 for p in obj.data.polygons)
            mat_count = len(obj.material_slots)

            # Drawing UI
            layout.label(text=f"{parent.name}", icon="OUTLINER_OB_ARMATURE")
            draw_labeled_row(layout, "Skinned Mesh:", skinned_mesh, ValueType.SKINNED_MESH, True, 0.8)
            if basic_mesh > 0:
                draw_labeled_row(layout, "Basic Mesh:", basic_mesh, ValueType.BASIC_MESH, True, 0.8)
            draw_labeled_row(layout, "Tris:", total_tri_count, ValueType.TRIS, True, 0.3, tri_count)
            draw_labeled_row(layout, "Materials:", total_mat_count, ValueType.MATERIALS, True, 0.6, mat_count)
            draw_labeled_row(layout, "Bones:", bone_count, ValueType.BONES, True, 0.5)
            return
        elif obj.type == "ARMATURE":
            # Count of tris and mats on the entire armature
            total_tri_count = sum(
                sum(len(p.vertices) - 2 for p in child.data.polygons) for child in obj.children if child.type == 'MESH')
            total_mat_count = sum(len(child.material_slots) for child in obj.children if child.type == "MESH")

            # Get the number of bones
            bone_count = len(obj.data.bones)

            # Skinned Mesh or Basic Mesh
            skinned_mesh = 0
            basic_mesh = 0
            for child in obj.children:
                if child.type == "MESH":
                    if any(mod.type == "ARMATURE" for mod in child.modifiers):
                        skinned_mesh += 1
                    else:
                        basic_mesh += 1

            # Drawing UI
            layout.label(text=f"{obj.name}", icon="OUTLINER_OB_ARMATURE")
            draw_labeled_row(layout, "Skinned Mesh:", skinned_mesh, ValueType.SKINNED_MESH, True, 0.8)
            if basic_mesh > 0:
                draw_labeled_row(layout, "Basic Mesh:", basic_mesh, ValueType.BASIC_MESH, True, 0.8)
            draw_labeled_row(layout, "Tris:", total_tri_count, ValueType.TRIS, True)
            draw_labeled_row(layout, "Materials:", total_mat_count, ValueType.MATERIALS, True, 0.6)
            draw_labeled_row(layout, "Bones:", bone_count, ValueType.BONES, True, 0.5)
            return
        else:
            # Count of tris and mats
            tri_count = sum(len(p.vertices) - 2 for p in obj.data.polygons)
            mat_count = len(obj.material_slots)

            # Drawing UI
            layout.label(text=f"{obj.name}", icon="MESH_CUBE")
            draw_labeled_row(layout, "Tris:", tri_count, ValueType.TRIS, False)
            draw_labeled_row(layout, "Materials:", mat_count, ValueType.MATERIALS, False, 0.6)
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