/*
 * susfs_ksu_bridge.c — Stub bridge between SUSFS and KernelSU (rsuntk fork)
 *
 * The kernel-level SUSFS patch (50_add_susfs_in_kernel-4.19.patch) references
 * functions that the KernelSU SUSFS patch (10_enable_susfs_for_ksu.patch)
 * would normally provide. Since that patch is incompatible with rsuntk's
 * KernelSU fork, we provide minimal stubs here.
 *
 * These stubs make SUSFS hiding functional (mount hiding, maps hiding, kstat
 * spoofing) without the full KernelSU integration (which would require
 * SELinux domain awareness).
 */

#include <linux/types.h>
#include <linux/export.h>
#include <linux/mount.h>
#include <linux/fs.h>

#ifdef CONFIG_KSU_SUSFS

/*
 * Check if the current process is running in KSU domain.
 * Stub: return false — SUSFS hiding applies to all processes.
 * This means hiding is less targeted but more comprehensive.
 */
bool susfs_is_current_ksu_domain(void)
{
	return false;
}
EXPORT_SYMBOL(susfs_is_current_ksu_domain);

/*
 * Check if the current process is a zygote-domain process.
 * Stub: return false.
 */
bool susfs_is_current_zygote_domain(void)
{
	return false;
}
EXPORT_SYMBOL(susfs_is_current_zygote_domain);

/*
 * Try to unmount all SUSFS-managed mounts.
 * Stub: no-op.
 */
void susfs_try_umount_all(void)
{
	/* no-op — mount hiding handled by sus_mount */
}
EXPORT_SYMBOL(susfs_try_umount_all);

/*
 * KernelSU try_umount callback.
 * Stub: no-op.
 */
void ksu_try_umount(const char *mnt, bool check_mnt, int flags)
{
	/* no-op */
}
EXPORT_SYMBOL(ksu_try_umount);

#endif /* CONFIG_KSU_SUSFS */
