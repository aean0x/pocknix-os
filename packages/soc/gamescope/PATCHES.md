# gamescope patches

What this package carries and why, one entry per patch. How each patch works is in its header.

## Base

Valve `3.16.31` (f6916aa, 2026-09-27)

Launch: logical landscape -W/-H, rotation autodetected from the primary plane (scanout on
sm8550 via kernel 0066, composite on sm8250); POCKNIX_PANEL_ROTATE_SHADER=1 forces
--force-composition-rotation for panels past the 1088-line rotator cap.

Last rebased: 2026-10-22 (0014/0015 native Wayland windows: focus, touch).

## Carried

### Input

- **0001** Touch works when gamescope runs nested: the Wayland backend wires up wl_touch.
  Source: ROCKNIX set.
- **0006** The gamepad cursor sprite no longer freezes when the cursor is driven through XTest.
  Source: ROCKNIX set.
- **0015** Android under Lepton gets real taps and swipes: a touch that goes down on an xdg-shell
  window passes through as wl_touch instead of Steam's pointer emulation, and keeps that mode
  until it lifts. X11 windows keep Steam's mode. Source: armada 0025, code verbatim, hunks
  re-anchored.

### Display and planes

- **0004** GAMESCOPE_FAKE_OUTPUT_MM sets a custom display physical size. Source: ROCKNIX set.
- **0012** A plane layout msm has no free hardware pipe for (test commit -ENODEV) counts as no fit
  instead of aborting. Source: sunshineinabox.
- **0013** The Steam overlay and MangoHud stay above the game: libliftoff sets a plane's mutable
  zpos from its layer, so msm's several primary planes (all zpos 0, else stacked by plane id)
  follow layer order. Source: ROCKNIX 0020 + 0022, verbatim.

### Frame pacing and colour

- **0009** FSR resolves to SGSR on SDR RGB, since the Steam Deck client offers no SGSR entry.
  The `fsr_means_sgsr` convar (default on) restores plain FSR. Source: ours.
- **0010** A frame that misses its vblank no longer waits a whole extra period: the fixed-refresh
  limiter releases frames by elapsed time since the last latch instead of a vblank-count
  divisor. The `limiter_use_elapsed_time` convar (default on) restores the divisor.
  Source: armada 0027.
- **0011** The composite skips identity colour LUTs, the larger half of sm8250's every-frame
  composite (the shaper + 3D LUT taps). Steam's 0.5 gamut wideness counts as native where planes
  cannot be colour managed (new `IBackend::SupportsPlaneColorManagement`), and a virtual white
  within 0.001 xy of the display's is no override. The `color_mgmt_skip_identity_luts` and
  `color_mgmt_native_gamut_without_plane_cm` convars (default on) turn each half off.
  Trap: a raw shaper/3D LUT override is never treated as identity. Source: ours.

### Steam focus

- **0014** An app whose only window is native Wayland (Lepton's Android container) leaves the
  launch spinner: mapped xdg-shell windows that carry an appid are reported in
  GAMESCOPE_FOCUSABLE_APPS/WINDOWS (id = top bit + xdg id, also published as
  GAMESCOPE_FOCUSED_WINDOW and honoured in GAMESCOPECTRL_BASELAYER_WINDOW).
  Source: armada 0024, verbatim.

## Not taken

- ROCKNIX 0008 --rotated-output-max-height: no such board yet.
- The revert of upstream e572411d (mangoapp frametimes): its early return skips
  `wlserver_app_presented()`, dropping the game's presentation feedback.

## Retired numbers

0005, 0007, 0008
