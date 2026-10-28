# FLAVA3 HDMI planning, recovery and ALLM

This change extends the PS5 HDMI-converter path with a shared output plan,
capability-aware colour/depth selection, native 4:2:0, bounded startup recovery
and Auto Low Latency Mode (ALLM). It remains experimental and opt-in. Hardware
qualification of this exact combined build is pending; this document describes
the implementation and software validation, not a supported-display guarantee.

## Scope and defaults

The changes are based on ps5-linux-patches main commit
`730b80eb95ffac399b421b5b0d10efa6563d5358`. They preserve its USB-C DisplayPort,
PS5 Pro GPU/SMU/firmware and fan-curve changes. The kernel build target remains
Linux 7.2.3; rebasing the patch repository does not change that kernel target.

Existing timing families and legacy VERDE behaviour are retained. This change
does not add HDMI VRR, HDMI DSC, new timing families or new VERDE capabilities.
Native USB-C capabilities provided by upstream are kept separate from the HDMI
converter. No fault-injection mechanism is included in the production patch.

| Parameter | Behaviour | Default |
|---|---|---|
| `hdmi.frl_4k120` | Enable experimental native FLAVA3 FRL | `0` |
| `hdmi.frl_yuv420` | `0`: disabled; `1`: legal fallback; `2`: prefer when permitted | `0` |
| `hdmi.frl_recovery` | Try bounded legal candidates after startup failure | `0` |
| `hdmi.allm` | `0`: off; `1`: follow DRM Game content; `2`: request on capable sink | `0` |
| `hdmi.allm_avi` | `0`: legacy AVI Game hint; `1`: stock AVI while ALLM enabled/capable; `2`: stock AVI always | `1` |

ALLM policy applies to the running output. AVI content policy takes effect on
the next modeset. `allm_sink`, `allm_valid` and `allm_active` expose capability
and confirmed state; `allm_active` is meaningful only when `allm_valid` is true.
A requested policy is not a confirmation that the sink received it.

## Shared plan and admission

The atomic connector state owns its plan by value. The plan contains timing,
input/output encoding, depth, colour range, HDR/BT.2020 state, transport and
connection generation. GPU stream projection and converter setup consume the
same choice. Probe-only plans do not publish live state.

Selection independently checks the internal DP path and external HDMI path.
The converter's four-lane, 8-Gbps envelope is 32 Gbps raw; that is not usable
video payload. HBR3 x4 has a separate nominal 25.92-Gbps internal budget before
additional constraints. A fit on one link cannot compensate for an overflow on
the other. Actual GPU validation and converter training remain required.

EDID format/depth/HDR capabilities, per-mode Y420 maps, metadata and GPU VSC-SDP
capability constrain the candidate. The conservative rate-4 admission rule is
retained. Firmware owns training; the patch does not expose a forced starting
rate. It does not imply uncompressed 4K120 RGB10 support.

The selector prefers legal TMDS where appropriate, preserves HDR and requested
depth bounds, and ranks legal format/depth alternatives. RGB fallback also
updates GPU colour conversion and range. The TMDS setup path propagates
pre-configuration, link and PHY errors so AMD cannot unmute a failed setup.

## Native 4:2:0

4:2:0 is offered only when sink mode maps, converter admission and GPU input
support agree. EDID maps are interpreted within their CTA extension and checked
against actual SVD collections. Header, length and checksum failures do not
create capabilities. The selected plan controls receiver packing, AVI and GPU
encoding/depth together.

An admitted mode is not proof of stable pixels. In particular, native 4K120420
picture, pacing and audio remain hardware qualification gates for this build.
A successful 4:2:2 fallback cannot be reported as a native 4:2:0 pass.

## Recovery, lifetime and errors

Recovery is bounded by a deterministic set of legal format/depth candidates and
an associated failure cache. It rechecks the same request before considering
the established lower-refresh escape path. That escape is an explicit fallback,
not success at the originally requested refresh. HDR and depth constraints still
apply. There is no continuous background link watchdog.

Failure state is tied to the sink generation and request. Disconnect, replacement
and new EDID invalidate stale work. The fallback worker checks the current
connector, active CRTC, saved plan and generation while holding the appropriate
DRM locks. Cleanup failure does not publish ready state or loop indefinitely.

The notification callback validates message bounds and EDID ownership, updates
state and schedules work. It avoids issuing setup commands while inside a
state-lock critical section. Live packet updates serialize against converter
setup. Confirmed state is published only after successful setup, health checks
and a final generation check; cleanup or unmute failure invalidates it.

## ALLM and AVI content

ALLM capability comes from validated HDMI Forum vendor/sink-capability blocks.
Unsupported sinks do not receive an enabled ALLM request. A Game content change
can update the converter's HF-VSIF without a modeset. Partial command failure
leaves state unknown and retryable, including when the next requested content
type is unchanged. Requested policy survives a recovery recommit.

TMDS's legacy AVI IT/Game hint can itself keep a TV in Game mode. The stock-AVI
policy separates that hint from HF-VSIF ALLM. Default policy1 suppresses the
legacy hint only while ALLM is requested on a capable sink; a non-ALLM sink
retains its legacy behaviour. Policy2 is an explicit stock-AVI control.

## Adjustments for current upstream

Upstream now has native USB-C DisplayPort alongside the HDMI converter. A
mechanical merge would apply converter-only rules to native DP. The integration
therefore uses upstream's physical-HDMI connector predicate for plan validation,
stream format projection, native420 agreement, RGB range, preferred-mode policy,
HDR, ALLM updates and fallback. Content-only modeset suppression and the added
Game content property are likewise restricted to the converter path. Native DP
continues to use its ordinary colour, packet and modeset behaviour.

The connector-specific `ps5_hdmi_get_edid()` API is retained, including override
precedence, teardown and duplicate ownership. The global EDID getter is removed.
Converter notification handling keeps the extended admission/recovery state and
uses an unaligned-safe length read. Initialisation/teardown retain both USB-C
workers/physical HPD and HDMI fallback-work lifecycle handling.

The new fan, thermal, Pro firmware and unrelated DC/USB changes are preserved;
they are not reimplemented by this HDMI patch. No firmware-staging service or
fan-curve setting is enabled as part of HDMI testing.

## Validation and remaining review gates

Software validation runs extracted production C, not a rewritten selector:

- Sanitized converter, packet, EDID, format/depth/HDR, native420 and budget tests.
- Setup, cleanup, partial-packet, unmute and stale-generation failures; actual
  fallback worker and AMD enable-path checks.
- Seven deliberate defective variants rejected by runtime assertions.
- Connector-specific EDID ownership/override/teardown and 72 routing/plan cases.
- 960 live ALLM routing cases covering HDMI, USB-C, virtual and missing links.
- 48 native-DP colour/range vectors equal to current upstream.
- Full patch apply/reverse, exact source identity, unchanged unrelated patch
  sections and preservation of new upstream functions in overlapping files.
- Strict source-delta checkpatch: zero errors, warnings and checks, excluding
  commit metadata, file-path and existing camel-case naming categories.
- Full Linux 7.2.3 kernel/modules builds. Existing unused HDCP-helper warnings
  remain; compilation alone does not qualify display behaviour.

Before merging, qualify the exact production binary for fixed-refresh
formats/depth/range/HDR, ALLM entry/exit and AVI controls, audible audio, reconnect
and sink replacement. Check bounded recovery on a separately identified test
build, then confirm a clean return to the known-good kernel. Native USB-C and
PS5 Pro runtime behaviour are not established by these HDMI software tests.
Capture/passthrough requires separate route-specific evidence.

Use the repository's build/install procedure and preserve a known-good kernel,
initrd and command line. Start with a temporary boot. Disabling opt-in controls
restores their defaults; keep a verified normal boot available for rollback.
