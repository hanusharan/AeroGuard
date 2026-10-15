"""Run a command, capture stdout/stderr to files, and write a resource summary (wall, user/sys CPU, peak RSS of the child)."""
import json, resource, subprocess, sys, time
out_json, stdout_path, stderr_path, *cmd = sys.argv[1:]
t0 = time.time()
with open(stdout_path, "w") as so, open(stderr_path, "w") as se:
    rc = subprocess.run(cmd, stdout=so, stderr=se).returncode
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
json.dump({"command": cmd, "exit_code": rc, "wall_seconds": time.time() - t0, "user_cpu_seconds": ru.ru_utime, "sys_cpu_seconds": ru.ru_stime,
           "max_rss_mb": ru.ru_maxrss / 1024.0, "utc_end": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(out_json, "w"), indent=2)
sys.exit(rc)
