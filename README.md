# KernelSU + SUSFS for Pixel 4a 5G (bramble)

Custom kernel build for Google Pixel 4a 5G with KernelSU (rsuntk fork) and SUSFS kernel-level root hiding.

## Target Device
- **Device**: Pixel 4a 5G (bramble)
- **Platform**: redbull
- **Kernel**: 4.19.x (pre-GKI)
- **Android**: 14

## Components
- **KernelSU**: rsuntk/KernelSU (non-GKI legacy support)
- **SUSFS**: simonpunk/susfs4ksu kernel-4.19 branch (kernel-level VFS hiding)
- **Base**: `android-msm-redbull-4.19-android14-qpr3` from Google

## Build
Trigger the GitHub Actions workflow manually. Outputs:
- `AnyKernel3.zip` — flash via custom recovery
- `Image.lz4-dtb` — raw kernel image
