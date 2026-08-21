---
name: dangling-pointer-detector
description: Configures GN, compiles, and runs Chromium unit/browser tests with PartitionAlloc Dangling Pointer Detection (DPD) to isolate raw_ptr lifetime violations.
---

# Dangling Pointer Detection (DPD) Skill

This skill provides step-by-step instructions and best practices to compile and run Chromium tests with PartitionAlloc's Dangling Pointer Detection (DPD) enabled.

---

## 1. Under-the-Hood Overview

Chromium uses a smart pointer wrapper called `raw_ptr<T>`. When Dangling Pointer Detection is active:
- The underlying `PartitionAlloc` memory allocator tracks pointer allocations.
- If the pointed-to memory is freed while a `raw_ptr<T>` is still alive and pointing to that address, the allocator registers the pointer as dangling.
- Upon test teardown or allocator cleanup, the test runner will crash or fail with a detailed backtrace showing exactly where the pointer went dangling and where the memory was originally allocated and freed.

---

## 2. GN Build Configuration

To use DPD, you must configure your build directory (e.g., `out/dpd` or `out/asan`) with specific arguments. 

There are two main ways to set this up, depending on the platform and build type:

### Setup A: Static Builds (Recommended for macOS)
Static builds avoid complex static initializer and symbol export issues with PartitionAlloc across dynamically linked libraries (`.dylib`s) on macOS.

Create or edit `args.gn` with:
```gn
is_component_build = false
enable_backup_ref_ptr_support = true
enable_dangling_raw_ptr_checks = true

# Recommended optimizations for faster compile and execution
is_debug = false
dcheck_always_on = true
symbol_level = 1
blink_symbol_level = 1
use_remoteexec = true
```

### Setup B: Component Builds (Linux, Windows, and Supported Configurations)
For component builds, PartitionAlloc-as-malloc (PA-E) and the allocator shim must be explicitly enabled to ensure symbols are properly exported and resolved across dynamic libraries.

Create or edit `args.gn` with:
```gn
is_component_build = true
use_partition_alloc_as_malloc = true
use_allocator_shim = true
enable_backup_ref_ptr_support = true
enable_dangling_raw_ptr_checks = true

# Recommended optimizations for faster compile and execution
is_debug = false
dcheck_always_on = true
symbol_level = 1
blink_symbol_level = 1
use_remoteexec = true
```

---

## 3. Compiling the Target

Once the build directory is generated (`gn gen out/dpd`), compile the desired test target. Most actor and browser-level tests belong to `unit_tests` or `browser_tests`:

```bash
autoninja -C out/dpd unit_tests
```

---

## 4. Running the Tests

To ensure that PartitionAlloc explicitly checks and reports dangling pointers during the test run, you **must** run the executable with the appropriate Feature Flags enabled:

```bash
./out/dpd/unit_tests --gtest_filter="YourTestClass.YourTestCase" --enable-features=PartitionAllocBackupRefPtr,PartitionAllocDanglingPtr
```

If a dangling pointer is present, the test will fail and output a report similar to:

```
[ FATAL:dangling_raw_ptr_checks.cc(...) ] The raw_ptr went dangling!
...
Stack trace of where the pointer went dangling:
    #0 ...
    #1 ...
Stack trace of where the memory was freed:
    #0 ...
    #1 ...
```

---

## 5. Troubleshooting Common Issues

### Error: `Chromium does not use BRP without PA-E`
- **Cause**: You enabled `enable_backup_ref_ptr_support = true` (BRP) but PartitionAlloc-as-malloc (`use_partition_alloc_as_malloc`) is evaluated as `false`.
- **Fix**: Ensure BRP is only enabled when PA-E is also enabled. If you are using a static build, PA-E is enabled by default. If you are in a component build, you must explicitly add `use_partition_alloc_as_malloc = true` to `args.gn`.

### Error: `undefined symbol: allocator_shim::IsDefaultAllocatorPartitionRootInitialized()`
- **Cause**: You are building a component build on macOS, and `use_partition_alloc_as_malloc` was enabled but `use_allocator_shim` was `false`. The base library tried to call allocator shim checks, but the allocator shim implementation was not compiled.
- **Fix**: Add `use_allocator_shim = true` to your `args.gn`.
