import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.util.Arrays;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

public class JavaUdpServer {

    public static void main(String args[])
    {
        System.out.println("JAVA UDP SERVER");
        DatagramSocket socket = null;
        int portNumber = 9008;

        try{
            socket = new DatagramSocket(portNumber);

            while(true) {
                byte[] receiveBuffer = new byte[1024];
                Arrays.fill(receiveBuffer, (byte)0);
                DatagramPacket receivePacket = new DatagramPacket(receiveBuffer, receiveBuffer.length);
                socket.receive(receivePacket);

                int nb = ByteBuffer.wrap(receiveBuffer).order(ByteOrder.LITTLE_ENDIAN).getInt();
                System.out.println(nb);

                var address = receivePacket.getSocketAddress();
                byte[] sendBuffer = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(nb+1).array();

                DatagramPacket sendPacket = new DatagramPacket(sendBuffer, sendBuffer.length, address);
                socket.send(sendPacket);
            }
        }
        catch(Exception e){
            e.printStackTrace();
        }
        finally {
            if (socket != null) {
                socket.close();
            }
        }
    }
}
