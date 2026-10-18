#!/usr/bin/env python
# =============================================================================
#  AutoReduction.py  (Debuggable version)
#  Purpose : Load an FBX, plot animation, export, then quit MotionBuilder.
#            Now includes debug traces to isolate potential issues.
#  Inputs  : Environment variables set by motionbuilder_auto_reduction.py
#            - MB_AUTOREDUCE_FBX : absolute path to source FBX
#            - MB_AUTOREDUCE_FPS : target frame rate (e.g., "30")
#            - MB_AUTOREDUCE_OUT : output FBX path (optional)
# =============================================================================

#参考：https://note.com/dftalk/n/n438923a5e59e

import os
import pyfbsdk as fb

from pyfbsdk import *

# ----------------------------------------------------------------------------- 
# Helper: unified debug output (console + MotionBuilder's Trace window)
# -----------------------------------------------------------------------------
def debug(message: str):
    fb.FBTrace(f"[AutoReduction] {message}")
    # If MotionBuilder was launched with -console, also print to stdout
    try:
        print(f"[AutoReduction] {message}")
    except Exception:
        pass  # Ignore if stdout is not available

def get_fps_mode(fps: int):
    """Convert fps value to FBTimeMode enum."""
    mapping = {
        24: fb.FBTimeMode.kFBTimeMode24Frames,
        25: fb.FBTimeMode.kFBTimeMode25Frames,
        30: fb.FBTimeMode.kFBTimeMode30Frames,
        60: fb.FBTimeMode.kFBTimeMode60Frames,
    }
    return mapping.get(fps, fb.FBTimeMode.kFBTimeMode30Frames)

def find_character_by_prefix(prefix: str) -> str | None:
    """Return the full name of the first Character whose LongName starts with prefix."""
    scene = FBSystem().Scene
    for character in scene.Characters:
        if character.LongName.startswith(prefix):
            return character
    return None

def create_save_options(has_animation=True, use_dialog=False, recent_files=False, 
                        embed_media=False, selection_only=True):
    """
    ファイルを保存する際のオプションを作成

    Args:
        has_animation (bool): アニメーションを含めるかどうか
        use_dialog (bool): ダイアログを表示するかどうか
        recent_files (bool): 最近使用したファイルを更新するかどうか
        embed_media (bool): メディアを埋め込むかどうか
        selection_only (bool): 選択した要素のみ保存するかどうか

    Returns:
        FBFbxOptions: 設定済みのオプションオブジェクト
    """
    opt = FBFbxOptions(False)  # do_load=True for load

    opt.SetAll(FBElementAction.kFBElementActionSave, has_animation)
    opt.ShowOptionsDialog = use_dialog
    opt.UpdateRecentFiles = recent_files
    opt.EmbedMedia = embed_media
    opt.SaveSelectedModelsOnly = selection_only
    if selection_only:
        # 選択保存の場合、シーン設定の要素を省く
        opt.BaseCameras = FBElementAction.kFBElementActionDiscard
        opt.CameraSwitcherSettings = FBElementAction.kFBElementActionDiscard
        opt.CurrentCameraSettings = FBElementAction.kFBElementActionDiscard
        opt.TransportSettings = FBElementAction.kFBElementActionDiscard
        opt.GlobalLightingSettings = FBElementAction.kFBElementActionDiscard

    return opt

def main():
    debug("Script started.")

    # -------------------------------------------------------------------------
    # 1. Retrieve parameters from environment
    # -------------------------------------------------------------------------
    fbx_path = os.environ.get("MB_AUTOREDUCE_FBX", "")
    fps_str  = os.environ.get("MB_AUTOREDUCE_FPS", "30")
    debug(f"Environment MB_AUTOREDUCE_FBX = '{fbx_path}'")
    debug(f"Environment MB_AUTOREDUCE_FPS = '{fps_str}'")

    if not fbx_path or not os.path.isfile(fbx_path):
        fb.FBMessageBox("AutoReduction‑Debug",
                        "Invalid or missing FBX path.\nCheck MB_AUTOREDUCE_FBX.",
                        "OK")
        debug("FBX path is invalid. Aborting.")
        return

    try:
        target_fps = int(fps_str)
    except ValueError:
        target_fps = 30
    debug(f"Target FPS resolved to {target_fps}")

    # -------------------------------------------------------------------------
    # 2. Load FBX
    # -------------------------------------------------------------------------
    app = fb.FBApplication()
    debug(f"Opening FBX '{fbx_path}' …")
    if not app.FileOpen(fbx_path):
        fb.FBMessageBox("AutoReduction‑Debug",
                        "Failed to open FBX file.\nSee console for details.",
                        "OK")
        debug("FileOpen returned False. Aborting.")
        return
    debug("FBX successfully loaded.")

    # -------------------------------------------------------------------------
    # 3. Set frame rate & plot animation
    # -------------------------------------------------------------------------
    time_mode = get_fps_mode(target_fps)
    fb.FBPlayerControl().SetTransportFps(time_mode)
    debug(f"Transport FPS set to {time_mode}.")

    character = find_character_by_prefix("chtoken")
    character.SelectModels(True, True, True, True)  # Select all models in the character

    plot_opts = fb.FBPlotOptions()
    plot_opts.PlotAllTakes          = True
    plot_opts.PlotOnFrame           = True
    plot_opts.RotationFilterToApply = (
        fb.FBRotationFilter.kFBRotationFilterGimbleKiller
    )
    debug("Starting FBPlotAnimationOnSelected …")
    FBSystem().CurrentTake.PlotTakeOnSelected(plot_opts)
    debug("Plotting finished.")

    character.FBDelete()

    # -------------------------------------------------------------------------
    # 4. Export selection to new binary FBX
    # -------------------------------------------------------------------------
    
    root, ext = os.path.splitext(fbx_path)
    out_path  = os.environ.get("MB_AUTOREDUCE_OUT") or f"{root}_{target_fps}fps{ext}"
    debug(f"Exporting selection to '{out_path}' (binary).")

    exp_opts = create_save_options()
    app.FileSave(out_path, exp_opts)

    # -------------------------------------------------------------------------
    # 5. Exit MotionBuilder without saving the current scene
    # -------------------------------------------------------------------------
    app.FileExit(False)  # False => do not save changes

main()
