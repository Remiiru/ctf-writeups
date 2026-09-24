# Scripts

## `cave_container_escape.sh`
Script de escape de contenedor Docker privilegiado via cgroup v1 release_agent (subsistema memory). Se coloca en /root/start.sh de un contenedor cuyo entrypoint es reescribible; al reiniciar el contenedor (matando el su - cave o el bash final hijo de PID1) corre como root y usa el release_agent para ejecutar comandos como root en el HOST, copiando /root/info.txt del host al overlay del contenedor. Desarrollado para el reto TryHackMe 'You're in a cave'.

## `cave_java_action_forge.java`
Forjador de objetos Action serializados (base64) para RCE en el reto TryHackMe 'You're in a cave' via deserializacion Java. Fija el serialVersionUID del server para que el objeto sea aceptado aunque compile con JDK distinto.
