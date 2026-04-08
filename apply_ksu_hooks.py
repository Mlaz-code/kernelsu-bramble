#!/usr/bin/env python3
"""Apply KernelSU manual hook patches to kernel 4.19 source files.

These 4 patches are REQUIRED for non-GKI kernels where kprobe doesn't work.
They hook into the kernel's VFS/exec paths so KernelSU can intercept syscalls.
"""
import re
import sys
import os

def patch_file(path, patches):
    """Apply patches to a file. Each patch is (marker, insert_before, code)."""
    with open(path) as f:
        content = f.read()

    for name, marker, code, insert_after in patches:
        if 'ksu_handle' in content and name in content:
            print(f"  SKIP: {name} already in {path}")
            continue

        if marker not in content:
            print(f"  WARN: marker not found for {name} in {path}: {marker[:60]}...")
            continue

        if insert_after:
            # Insert code AFTER the marker line
            idx = content.find(marker)
            # Find end of the marker line
            end = content.find('\n', idx)
            content = content[:end+1] + code + '\n' + content[end+1:]
        else:
            # Insert code BEFORE the marker line
            idx = content.find(marker)
            content = content[:idx] + code + '\n' + content[idx:]

        print(f"  OK: {name} patched in {path}")

    with open(path, 'w') as f:
        f.write(content)


def patch_exec_c(kernel_dir):
    """Patch fs/exec.c — add ksu_handle_execveat in do_execveat_common."""
    path = os.path.join(kernel_dir, 'fs/exec.c')
    print(f"Patching {path}...")

    with open(path) as f:
        content = f.read()

    if 'ksu_handle_execveat' in content:
        print("  SKIP: already patched")
        return

    # Add extern declarations before do_execveat_common
    decl = """
#ifdef CONFIG_KSU
extern bool ksu_execveat_hook __read_mostly;
extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr, void *argv,
			void *envp, int *flags);
extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr,
				 void *argv, void *envp, int *flags);
#endif
"""

    hook = """#ifdef CONFIG_KSU
	if (unlikely(ksu_execveat_hook))
		ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
	else
		ksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);
#endif
"""

    # Find do_execveat_common function
    match = re.search(r'^(static\s+int\s+do_execveat_common\b.*?\{)', content, re.MULTILINE | re.DOTALL)
    if not match:
        print("  WARN: do_execveat_common not found")
        return

    # Insert declarations before the function
    func_start = match.start()
    content = content[:func_start] + decl + content[func_start:]

    # Now find the function body and insert hook after opening brace
    # Re-find since we modified content
    match = re.search(r'(static\s+int\s+do_execveat_common\b[^{]*\{)', content, re.MULTILINE | re.DOTALL)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + '\n' + hook + content[insert_pos:]

    with open(path, 'w') as f:
        f.write(content)
    print("  OK: fs/exec.c patched")


def patch_open_c(kernel_dir):
    """Patch fs/open.c — add ksu_handle_faccessat in do_faccessat."""
    path = os.path.join(kernel_dir, 'fs/open.c')
    print(f"Patching {path}...")

    with open(path) as f:
        content = f.read()

    if 'ksu_handle_faccessat' in content:
        print("  SKIP: already patched")
        return

    decl = """
#ifdef CONFIG_KSU
extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user, int *mode,
			 int *flags);
#endif
"""
    hook = """#ifdef CONFIG_KSU
	ksu_handle_faccessat(&dfd, &filename, &mode, NULL);
#endif
"""

    # Find do_faccessat function
    match = re.search(r'^(long\s+do_faccessat\b.*?\{)', content, re.MULTILINE | re.DOTALL)
    if not match:
        print("  WARN: do_faccessat not found")
        return

    # Insert declarations before function
    content = content[:match.start()] + decl + content[match.start():]

    # Re-find and insert hook after opening brace
    match = re.search(r'(long\s+do_faccessat\b[^{]*\{)', content, re.MULTILINE | re.DOTALL)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + '\n' + hook + content[insert_pos:]

    with open(path, 'w') as f:
        f.write(content)
    print("  OK: fs/open.c patched")


def patch_read_write_c(kernel_dir):
    """Patch fs/read_write.c — add ksu_handle_vfs_read in vfs_read."""
    path = os.path.join(kernel_dir, 'fs/read_write.c')
    print(f"Patching {path}...")

    with open(path) as f:
        lines = f.readlines()

    if any('ksu_handle_vfs_read' in l for l in lines):
        print("  SKIP: already patched")
        return

    decl_lines = [
        '#ifdef CONFIG_KSU\n',
        'extern bool ksu_vfs_read_hook __read_mostly;\n',
        'extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr,\n',
        '\t\t\tsize_t *count_ptr, loff_t **pos);\n',
        '#endif\n',
    ]

    hook_lines = [
        '#ifdef CONFIG_KSU\n',
        '\tif (unlikely(ksu_vfs_read_hook))\n',
        '\t\tksu_handle_vfs_read(&file, &buf, &count, &pos);\n',
        '#endif\n',
    ]

    # Find the FIRST "ssize_t vfs_read(" — must be the function definition, not a declaration
    new_lines = []
    found_func = False
    inserted_decl = False
    inserted_hook = False

    for i, line in enumerate(lines):
        # Insert decl before the first vfs_read function definition
        if not inserted_decl and re.match(r'^ssize_t vfs_read\(struct file', line):
            new_lines.extend(decl_lines)
            inserted_decl = True
            found_func = True

        new_lines.append(line)

        # Insert hook after the opening brace of vfs_read, before FMODE_READ check
        if found_func and not inserted_hook:
            if 'FMODE_READ' in line:
                # Insert hook before this line (replace last added line, insert hook before it)
                new_lines.pop()  # remove the FMODE_READ line
                new_lines.extend(hook_lines)
                new_lines.append(line)  # re-add the FMODE_READ line
                inserted_hook = True

    if inserted_hook:
        with open(path, 'w') as f:
            f.writelines(new_lines)
        print("  OK: fs/read_write.c patched")
    else:
        print("  WARN: Could not find vfs_read insertion point")


def patch_stat_c(kernel_dir):
    """Patch fs/stat.c — add ksu_handle_stat in vfs_statx."""
    path = os.path.join(kernel_dir, 'fs/stat.c')
    print(f"Patching {path}...")

    with open(path) as f:
        content = f.read()

    if 'ksu_handle_stat' in content:
        print("  SKIP: already patched")
        return

    decl = """
#ifdef CONFIG_KSU
extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);
#endif
"""
    hook = """#ifdef CONFIG_KSU
	ksu_handle_stat(&dfd, &filename, &flags);
#endif
"""

    # Find vfs_statx function
    match = re.search(r'^(int\s+vfs_statx\b.*?\{)', content, re.MULTILINE | re.DOTALL)
    if not match:
        print("  WARN: vfs_statx not found")
        return

    # Insert declarations before function
    content = content[:match.start()] + decl + content[match.start():]

    # Re-find and insert hook after opening brace
    match = re.search(r'(int\s+vfs_statx\b[^{]*\{)', content, re.MULTILINE | re.DOTALL)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + '\n' + hook + content[insert_pos:]

    with open(path, 'w') as f:
        f.write(content)
    print("  OK: fs/stat.c patched")


if __name__ == '__main__':
    kernel_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    print(f"=== Applying KernelSU manual hook patches to {kernel_dir} ===")
    patch_exec_c(kernel_dir)
    patch_open_c(kernel_dir)
    patch_read_write_c(kernel_dir)
    patch_stat_c(kernel_dir)
    print("=== Done ===")
