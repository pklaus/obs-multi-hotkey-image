#!/usr/bin/env python

"""
Reveal any image from a folder using a dedicated hotkey.
Works in push-to-show mode by default.
The hotkey for each image file can be configured
in the "Hotkeys" section of OBS' settings.

By @pklaus
"""

import obspython as obs
import enum, glob, os, re


class Mode(enum.Enum):
    PushToShow = enum.auto()
    PushToToggle = enum.auto()


hotkeys = {}
current_image = None
target_source = None
mode = Mode.PushToShow
image_folder = os.path.dirname(__file__) + "/images"


def get_available_images():  # -> List[str]:
    all_files_in_image_folder = glob.glob(image_folder + "/*")
    all_image_files = [
        f
        for f in all_files_in_image_folder
        if re.match(r".*\.(bmp|tga|png|jpeg|jpg|gif|psd|webp)$", f)
    ]
    return [os.path.basename(i) for i in all_image_files]


def full_image_path(image: str) -> str:
    return image_folder + f"/{image}"


def script_load(settings):
    print(f"--- {os.path.basename(__file__)} loaded ---")
    print(f"    with the following images: {get_available_images()}")

    # create Hotkey in global OBS Settings
    for i, image in enumerate(get_available_images()):
        name = f"SHORTCUT {i}"
        kotkey_id = obs.obs_hotkey_register_frontend(
            name, f"Multi-Hotkey-Image: '{image}'", hotkey_callback_factory(image)
        )
        hotkeys[kotkey_id] = name

    # load hotkeys from script save file
    for hotkey_id in hotkeys:
        hotkey_data_array_from_settings = obs.obs_data_get_array(
            settings, hotkeys[hotkey_id]
        )
        obs.obs_hotkey_load(hotkey_id, hotkey_data_array_from_settings)
        obs.obs_data_array_release(hotkey_data_array_from_settings)


def script_save(settings):
    # save hotkeys in script properties
    for hotkey_id in hotkeys:
        obs.obs_data_set_array(
            settings, hotkeys[hotkey_id], obs.obs_hotkey_save(hotkey_id)
        )


def script_update(settings):
    # print("script update")
    global target_source, mode, image_folder

    target_source = obs.obs_data_get_string(settings, "source_select_list") or None

    image_folder = obs.obs_data_get_string(settings, "image_folder")

    toggle_mode = obs.obs_data_get_bool(settings, "toggle_mode")
    toggle_mode
    if toggle_mode:
        mode = Mode.PushToToggle
    else:
        mode = Mode.PushToShow

    if mode == Mode.PushToShow:
        set_source_visibility(show=False)


def script_properties():
    # print("script props")
    props = obs.obs_properties_create()

    drop_list = obs.obs_properties_add_list(
        props,
        "source_select_list",
        "Image Source",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    obs.obs_property_list_add_string(drop_list, "", "")
    sources = obs.obs_enum_sources()
    for src in sources:
        if obs.obs_source_get_unversioned_id(src) != "image_source":
            continue
        obs.obs_property_list_add_string(
            drop_list, obs.obs_source_get_name(src), obs.obs_source_get_name(src)
        )
    obs.source_list_release(sources)

    obs.obs_properties_add_path(
        props,
        "image_folder",
        "Images Folder",
        obs.OBS_PATH_DIRECTORY,
        None,
        image_folder,
    )

    obs.obs_properties_add_bool(props, "toggle_mode", "toggle mode")

    return props


def script_description():
    return __doc__



def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "image_folder", image_folder)


def hotkey_callback_factory(image: str):
    def hotkey_callback(is_pressed):
        # print("-- Hotkey for image={} (pressed: {})".format(image, is_pressed))
        global current_image
        current_image = image
        if mode == Mode.PushToShow:
            set_source_visibility(show=is_pressed)
        if mode == Mode.PushToToggle and is_pressed:
            set_source_visibility(toggle=True)

    return hotkey_callback


def get_current_image_file(source):
    settings = obs.obs_source_get_settings(source)
    current_file = obs.obs_data_get_string(settings, "file")
    obs.obs_data_release(settings)
    return current_file


def update_image_file(source, filename):
    """ Returns True if the image had to be changed. """
    if get_current_image_file(source) == filename:
        return False
    print(f"image source file updated to: {os.path.basename(filename)} ({filename})")
    settings = obs.obs_data_create()
    obs.obs_data_set_string(settings, "file", filename)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    return True


def set_source_visibility(show: bool = None, toggle: bool = False):
    # print(f"set_source_visibility(show={show}, toggle={toggle})")
    scene_sources = obs.obs_frontend_get_scenes()
    for scn_src in scene_sources:
        scn = obs.obs_scene_from_source(scn_src)
        scn_items = obs.obs_scene_enum_items(scn)
        for itm in scn_items:
            itm_src = obs.obs_sceneitem_get_source(itm)
            if obs.obs_source_get_name(itm_src) == target_source:
                image_changed = update_image_file(
                    itm_src, full_image_path(current_image)
                )
                if toggle:
                    currently_visible = obs.obs_sceneitem_visible(itm)
                    if not (currently_visible and image_changed):
                        obs.obs_sceneitem_set_visible(
                            itm, not obs.obs_sceneitem_visible(itm)
                        )
                else:
                    obs.obs_sceneitem_set_visible(itm, show)
        obs.sceneitem_list_release(scn_items)
    obs.source_list_release(scene_sources)
