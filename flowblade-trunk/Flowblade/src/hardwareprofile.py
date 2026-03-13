"""
    Hardware profile module for optimizing Flowblade on specific hardware.

    Provides detection and tuning for constrained systems like
    Lenovo ThinkPad X270 (Intel i5-7200U, 8GB RAM, Intel HD 620).
"""

import os
import multiprocessing

import editorpersistance
import appconsts

# Hardware profile constants
PROFILE_GENERIC = "generic"
PROFILE_LOW_POWER_INTEL = "low_power_intel"

# Memory thresholds in GB
MEMORY_LOW = 8
MEMORY_MEDIUM = 16

# Undo stack sizes by memory tier
UNDO_STACK_LOW_MEM = 15
UNDO_STACK_MED_MEM = 25

# MLT consumer tuning for low-power Intel
LOW_POWER_RESCALE = "bilinear"  # bicubic is default but heavier on iGPU
LOW_POWER_RENDER_THREADS_CAP = 2  # i5-7200U is 2C/4T, cap threads to avoid thrash

def get_total_memory_gb():
    """Returns total system RAM in GB."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    return kb / (1024 * 1024)
    except:
        pass
    return 16  # safe fallback

def get_cpu_model():
    """Returns CPU model string from /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":")[1].strip()
    except:
        pass
    return ""

def has_vaapi_support():
    """Check if VAAPI render node exists (Intel iGPU hw accel)."""
    return os.path.exists("/dev/dri/renderD128")

def detect_profile():
    """Detect hardware profile based on system characteristics."""
    mem_gb = get_total_memory_gb()
    cpu = get_cpu_model().lower()
    cpu_count = multiprocessing.cpu_count()

    is_intel_igpu = has_vaapi_support() and ("intel" in cpu or "i5" in cpu or "i7" in cpu)
    is_low_mem = mem_gb <= MEMORY_LOW
    is_low_core = cpu_count <= 4

    if is_intel_igpu and (is_low_mem or is_low_core):
        return PROFILE_LOW_POWER_INTEL

    return PROFILE_GENERIC

def get_optimal_render_threads():
    """Return optimal render thread count for this system.

    For dual-core hyperthreaded CPUs (like i5-7200U), using all 4 logical
    cores for rendering causes context-switch overhead. Cap at physical cores.
    """
    cpu_count = multiprocessing.cpu_count()

    if cpu_count <= 4:
        return min(cpu_count, LOW_POWER_RENDER_THREADS_CAP)

    return max(1, cpu_count // 2)

def get_optimal_undo_stack():
    """Return undo stack size tuned for available memory."""
    mem_gb = get_total_memory_gb()

    if mem_gb <= MEMORY_LOW:
        return UNDO_STACK_LOW_MEM
    elif mem_gb <= MEMORY_MEDIUM:
        return UNDO_STACK_MED_MEM

    return editorpersistance.UNDO_STACK_DEFAULT

def get_playback_rescale():
    """Return rescale algorithm appropriate for hardware.

    bilinear is significantly faster than bicubic on Intel HD 620
    with minimal visual difference at monitor preview sizes.
    """
    profile = detect_profile()
    if profile == PROFILE_LOW_POWER_INTEL:
        return LOW_POWER_RESCALE
    return "bicubic"

def get_optimal_proxy_size():
    """Return proxy size for memory-constrained systems."""
    mem_gb = get_total_memory_gb()
    if mem_gb <= MEMORY_LOW:
        return appconsts.PROXY_SIZE_HALF
    return appconsts.PROXY_SIZE_FULL

def apply_profile_to_prefs(prefs):
    """Apply hardware-detected optimizations to editor preferences.

    Only adjusts values that are still at defaults - respects user overrides.
    Returns True if any changes were made.
    """
    changed = False
    profile = detect_profile()

    if profile == PROFILE_GENERIC:
        return False

    # Render threads: bump from default 1 to optimal for this CPU
    if prefs.perf_render_threads == 1:
        optimal_threads = get_optimal_render_threads()
        if optimal_threads != prefs.perf_render_threads:
            prefs.perf_render_threads = optimal_threads
            changed = True

    # Frame dropping: enable on low-power for smoother playback
    if prefs.perf_drop_frames == False:
        prefs.perf_drop_frames = True
        changed = True

    # Undo stack: reduce on low memory systems
    if prefs.undos_max == editorpersistance.UNDO_STACK_DEFAULT:
        optimal_undos = get_optimal_undo_stack()
        if optimal_undos != prefs.undos_max:
            prefs.undos_max = optimal_undos
            changed = True

    # Proxy size: use half on 8GB systems
    if prefs.tline_render_size == appconsts.PROXY_SIZE_FULL:
        optimal_proxy = get_optimal_proxy_size()
        if optimal_proxy != prefs.tline_render_size:
            prefs.tline_render_size = optimal_proxy
            changed = True

    # Sequential rendering: always on for low-power (avoid parallel job OOM)
    if prefs.render_jobs_sequentially == False:
        prefs.render_jobs_sequentially = True
        changed = True

    return changed

def print_hardware_summary():
    """Print detected hardware info at startup."""
    profile = detect_profile()
    if profile == PROFILE_GENERIC:
        return

    mem_gb = get_total_memory_gb()
    cpu = get_cpu_model()
    cpu_count = multiprocessing.cpu_count()
    vaapi = has_vaapi_support()

    print("--- Hardware Profile: %s ---" % profile)
    print("  CPU: %s (%d threads)" % (cpu, cpu_count))
    print("  RAM: %.1f GB" % mem_gb)
    print("  VAAPI: %s" % ("available" if vaapi else "not found"))
    print("  Render threads: %d" % get_optimal_render_threads())
    print("  Playback rescale: %s" % get_playback_rescale())
    print("  Proxy size: %s" % ("half" if get_optimal_proxy_size() == appconsts.PROXY_SIZE_HALF else "full"))
    print("---")
